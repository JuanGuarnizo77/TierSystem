"""
Controlador de Protocolo de Muestreo en Campo y Captura IoT - TierSystem API.
Gestiona el ciclo de vida del muestreo físico:
1. Generación de cuadrícula de puntos según área en hectáreas del predio.
2. Ingesta de telemetría estabilizada desde la sonda ESP32 (Modbus RTU / RS485).
3. Persistencia de perforaciones georreferenciadas en 3D (latitud, longitud, altitud GPS).
4. Consolidación de medias y emisión del diagnóstico edafológico definitivo.
"""

import json

from django.db import transaction
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsLaboratorista
from apps.analisis.models import PuntoMuestreo
from apps.sensores.views import captura_estable
from apps.ia_recomendaciones.views import (
    calcular_diagnostico_edafologico,
    _guardar_diagnostico_solicitud,
)
from apps.solicitudes.models import SolicitudAnalisis

# Variables fisicoquímicas evaluadas en cada punto de suelo
CAMPOS_SENSOR = [
    'humedad', 'temperatura', 'conductividad',
    'ph', 'nitrogeno', 'fosforo', 'potasio',
]


def _num_puntos(hectareas):
    """
    Algoritmo de Densidad de Muestreo por Hectárea.
    Calcula el número estadísticamente representativo de perforaciones de tierra:
    - Hasta 1 ha: 5 puntos
    - 1 a 5 ha: 10 puntos
    - 5 a 10 ha: 15 puntos
    - Mayor a 10 ha: 20 puntos (tope de representatividad)
    """
    h = float(hectareas)
    if h <= 1:
        return 5
    if h <= 5:
        return 10
    if h <= 10:
        return 15
    return 20


def _f(v):
    """Convierte de forma segura un valor numérico decimal a float o None."""
    return float(v) if v is not None else None


def _punto_dict(p):
    """
    Serializa una instancia de PuntoMuestreo a un diccionario limpio para JSON.
    Incluye coordenadas tridimensionales y las lecturas químicas recolectadas.
    """
    return {
        'id': p.id,
        'numero': p.numero,
        'estado': p.estado,
        'latitud': _f(p.latitud),
        'longitud': _f(p.longitud),
        'altitud': _f(p.altitud),
        'fecha_toma': p.fecha_toma,
        'humedad': _f(p.humedad),
        'temperatura': _f(p.temperatura),
        'conductividad': _f(p.conductividad),
        'ph': _f(p.ph),
        'nitrogeno': _f(p.nitrogeno),
        'fosforo': _f(p.fosforo),
        'potasio': _f(p.potasio),
    }


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def muestreo_view(request, solicitud_id):
    """
    GET /api/v1/laboratorista/muestreo/<solicitud_id>/
    Retorna la ficha técnica de la solicitud y el listado de puntos de muestreo.
    Si la modalidad es VISITA y no se han generado los puntos, los crea en lote
    mediante bulk_create() aplicando el algoritmo de densidad por hectáreas.
    """
    # Consulta optimizada con select_related para evitar N+1 queries sobre terreno y agricultor
    s = get_object_or_404(
        SolicitudAnalisis.objects.select_related('terreno', 'agricultor'),
        pk=solicitud_id,
        laboratorista_asignado=request.user,
    )

    puntos = []
    if s.modalidad == 'VISITA':
        qs = PuntoMuestreo.objects.filter(solicitud=s)
        # Si aún no existen puntos generados para esta visita técnica, los inicializa en lote
        if not qs.exists():
            PuntoMuestreo.objects.bulk_create([
                PuntoMuestreo(solicitud=s, numero=i)
                for i in range(1, _num_puntos(s.terreno.hectareas) + 1)
            ])
            qs = PuntoMuestreo.objects.filter(solicitud=s)
        # Serializa la cuadrícula de puntos ordenada por índice secuencial
        puntos = [_punto_dict(p) for p in qs.order_by('numero')]

    # Conteo de puntos que ya fueron medidos y guardados con éxito
    tomados = sum(1 for p in puntos if p['estado'] == 'TOMADO')
    return Response({
        'solicitud': {
            'id': s.id,
            'estado': s.estado,
            'modalidad': s.modalidad,
            'modalidad_texto': s.get_modalidad_display(),
            'cultivo_deseado': s.cultivo_deseado,
            'agricultor': s.agricultor.get_full_name() or s.agricultor.username,
            'terreno_nombre': s.terreno.nombre,
            'terreno_ubicacion': s.terreno.ubicacion,
            'hectareas': float(s.terreno.hectareas),
            'tiene_analisis': hasattr(s, 'analisis_resultado'),
        },
        'total_puntos': len(puntos),
        'puntos_tomados': tomados,
        'puntos': puntos,
    })


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def sensor_view(request):
    """
    GET /api/v1/laboratorista/muestreo/sensor/
    Invoca el mecanismo anti-ruido captura_estable() para filtrar oscilaciones
    galvánicas y extraer la moda estadística de las lecturas del ESP32.
    """
    # Reutiliza el controlador web pasando la solicitud WSGI subyacente
    resp = captura_estable(request._request)
    data = json.loads(resp.content)
    if data.get('estado') != 'ok':
        return Response(
            {'error': data.get('mensaje', 'No se pudo leer el sensor.')},
            status=503,
        )
    return Response({
        'mensaje': data.get('mensaje', ''),
        'datos': data['datos'],
    })


@api_view(['POST'])
@permission_classes([IsLaboratorista])
def guardar_punto_view(request, punto_id):
    """
    POST /api/v1/laboratorista/muestreo/puntos/<punto_id>/guardar/
    Persiste las variables fisicoquímicas y coordenadas GPS del punto físico.
    Body JSON:
    - Obligatorios: humedad, temperatura, conductividad, ph, nitrogeno, fosforo, potasio
    - Opcionales: latitud, longitud, altitud
    """
    # Verifica que el punto pertenezca a una orden asignada al técnico actual
    punto = get_object_or_404(
        PuntoMuestreo,
        pk=punto_id,
        solicitud__laboratorista_asignado=request.user,
    )

    # Validación de tipos numéricos para todos los parámetros del sensor
    valores = {}
    for campo in CAMPOS_SENSOR:
        try:
            valores[campo] = round(float(request.data.get(campo)), 2)
        except (TypeError, ValueError):
            return Response(
                {'error': f'Valor inválido o faltante: {campo}.'}, status=400
            )

    # Asignación dinámica de valores químicos validados
    for campo, valor in valores.items():
        setattr(punto, campo, valor)

    # Función auxiliar para sanitizar coordenadas GPS y altitud opcionales
    def _opcional(nombre, decimales):
        v = request.data.get(nombre)
        if v is None:
            return None
        try:
            return round(float(v), decimales)
        except (TypeError, ValueError):
            return None

    # Georreferenciación 3D de la perforación
    lat = _opcional('latitud', 7)
    lon = _opcional('longitud', 7)
    alt = _opcional('altitud', 2)
    if lat is not None:
        punto.latitud = lat
    if lon is not None:
        punto.longitud = lon
    if alt is not None:
        punto.altitud = alt

    # Actualización del ciclo de vida del punto a TOMADO
    punto.fecha_toma = timezone.now()
    punto.estado = 'TOMADO'
    punto.save()

    # Recarga desde base de datos y respuesta al cliente móvil
    punto.refresh_from_db()
    return Response({
        'mensaje': 'Punto guardado correctamente.',
        'punto': _punto_dict(punto),
    })


@api_view(['POST'])
@permission_classes([IsLaboratorista])
def generar_analisis_view(request, solicitud_id):
    """
    POST /api/v1/laboratorista/muestreo/<solicitud_id>/generar/
    Consolida las muestras y emite el informe final del estudio de suelo:
    - En VISITA: Calcula la media aritmética (SQL Avg) de todos los puntos en estado TOMADO.
      Si faltan puntos por tomar, rechaza con HTTP 409 Conflict salvo que traiga {"parcial": true}.
    - En LLEVAR_MUESTRA: Recibe directamente el diccionario "datos" medido en la sede técnica.
    Ejecuta el motor agronómico edafológico y persiste atómicamente en RegistroAnalisis
    marcando la orden en estado 'COMPLETADA'.
    """
    s = get_object_or_404(
        SolicitudAnalisis.objects.select_related('terreno'),
        pk=solicitud_id,
        laboratorista_asignado=request.user,
    )

    # Valida que la solicitud se encuentre en un estado operativo editable
    if s.estado not in ('ASIGNADA', 'EN_PROCESO'):
        return Response(
            {'error': 'Esta solicitud ya no admite generar un análisis.'},
            status=400,
        )

    valores = {}
    puntos_usados = 0

    if s.modalidad == 'VISITA':
        # Procesamiento para muestreo en finca con cuadrícula física
        qs = PuntoMuestreo.objects.filter(solicitud=s)
        total = qs.count()
        tomados = qs.filter(estado='TOMADO')
        puntos_usados = tomados.count()

        if puntos_usados == 0:
            return Response({'error': 'Aún no has tomado ningún punto.'}, status=400)

        # Regla de integridad: Exige completar todos los puntos a menos que se autorice cierre parcial
        if puntos_usados < total and not request.data.get('parcial'):
            return Response(
                {'error': f'Faltan puntos por tomar ({puntos_usados} de {total}).'},
                status=409,
            )

        # Agregación SQL optimizada mediante diccionario de promedios Avg
        prom = tomados.aggregate(**{c: Avg(c) for c in CAMPOS_SENSOR})
        for campo in CAMPOS_SENSOR:
            if prom[campo] is None:
                return Response(
                    {'error': f'Los puntos tomados no tienen valor de {campo}.'},
                    status=400,
                )
            valores[campo] = round(float(prom[campo]), 2)
    else:
        # Modalidad presencial en sede física: lectura directa de muestra homogeneizada
        datos = request.data.get('datos') or {}
        puntos_usados = 1
        for campo in CAMPOS_SENSOR:
            try:
                valores[campo] = round(float(datos.get(campo)), 2)
            except (TypeError, ValueError, AttributeError):
                return Response(
                    {'error': f'Valor inválido o faltante: {campo}.'}, status=400
                )

    # Identificación del cultivo objetivo del campesino para priorizar en recomendaciones
    preferencia = s.cultivo_deseado
    if preferencia == 'No especificado':
        preferencia = ''

    # Ejecución del motor agronómico determinístico con ponderación de nutrientes
    diagnostico = calcular_diagnostico_edafologico(
        valores['humedad'], valores['temperatura'], valores['conductividad'],
        valores['ph'], valores['nitrogeno'], valores['fosforo'], valores['potasio'],
        preferencia=preferencia,
    )

    # Transacción atómica: asegura que el guardado de RegistroAnalisis y RecomendacionAnalisis sea indivisible
    with transaction.atomic():
        _guardar_diagnostico_solicitud(
            s.id, diagnostico,
            valores['humedad'], valores['temperatura'], valores['conductividad'],
            valores['ph'], valores['nitrogeno'], valores['fosforo'], valores['potasio'],
        )

    return Response({
        'mensaje': 'Análisis generado correctamente.',
        'solicitud_id': s.id,
        'puntos_usados': puntos_usados,
        'valores': valores,
    })