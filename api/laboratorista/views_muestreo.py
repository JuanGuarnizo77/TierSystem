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

CAMPOS_SENSOR = [
    'humedad', 'temperatura', 'conductividad',
    'ph', 'nitrogeno', 'fosforo', 'potasio',
]


def _num_puntos(hectareas):
    """Misma regla de la web."""
    h = float(hectareas)
    if h <= 1:
        return 5
    if h <= 5:
        return 10
    if h <= 10:
        return 15
    return 20


def _f(v):
    return float(v) if v is not None else None


def _punto_dict(p):
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
    Devuelve la solicitud y sus puntos de muestreo.
    Si la modalidad es VISITA y no hay puntos, los crea.
    """
    s = get_object_or_404(
        SolicitudAnalisis.objects.select_related('terreno', 'agricultor'),
        pk=solicitud_id,
        laboratorista_asignado=request.user,
    )

    puntos = []
    if s.modalidad == 'VISITA':
        qs = PuntoMuestreo.objects.filter(solicitud=s)
        if not qs.exists():
            PuntoMuestreo.objects.bulk_create([
                PuntoMuestreo(solicitud=s, numero=i)
                for i in range(1, _num_puntos(s.terreno.hectareas) + 1)
            ])
            qs = PuntoMuestreo.objects.filter(solicitud=s)
        puntos = [_punto_dict(p) for p in qs.order_by('numero')]

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
    Lectura estable del ESP32 (últimos segundos). Usa la misma lógica de la web.
    """
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
    Body: humedad, temperatura, conductividad, ph, nitrogeno, fosforo, potasio
          (obligatorios) y latitud, longitud, altitud (opcionales).
    """
    punto = get_object_or_404(
        PuntoMuestreo,
        pk=punto_id,
        solicitud__laboratorista_asignado=request.user,
    )

    valores = {}
    for campo in CAMPOS_SENSOR:
        try:
            valores[campo] = round(float(request.data.get(campo)), 2)
        except (TypeError, ValueError):
            return Response(
                {'error': f'Valor inválido o faltante: {campo}.'}, status=400
            )

    for campo, valor in valores.items():
        setattr(punto, campo, valor)

    def _opcional(nombre, decimales):
        v = request.data.get(nombre)
        if v is None:
            return None
        try:
            return round(float(v), decimales)
        except (TypeError, ValueError):
            return None

    lat = _opcional('latitud', 7)
    lon = _opcional('longitud', 7)
    alt = _opcional('altitud', 2)
    if lat is not None:
        punto.latitud = lat
    if lon is not None:
        punto.longitud = lon
    if alt is not None:
        punto.altitud = alt

    punto.fecha_toma = timezone.now()
    punto.estado = 'TOMADO'
    punto.save()

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
    VISITA: promedia los puntos TOMADO. Si faltan puntos responde 409,
            salvo que el body traiga {"parcial": true}.
    LLEVAR_MUESTRA: el body trae {"datos": {humedad, temperatura, conductividad,
            ph, nitrogeno, fosforo, potasio}} leídos del sensor.
    Guarda el análisis y marca la solicitud como COMPLETADA.
    No usa valores de relleno: si faltan datos, responde con error.
    """
    s = get_object_or_404(
        SolicitudAnalisis.objects.select_related('terreno'),
        pk=solicitud_id,
        laboratorista_asignado=request.user,
    )

    if s.estado not in ('ASIGNADA', 'EN_PROCESO'):
        return Response(
            {'error': 'Esta solicitud ya no admite generar un análisis.'},
            status=400,
        )

    valores = {}
    puntos_usados = 0

    if s.modalidad == 'VISITA':
        qs = PuntoMuestreo.objects.filter(solicitud=s)
        total = qs.count()
        tomados = qs.filter(estado='TOMADO')
        puntos_usados = tomados.count()
        if puntos_usados == 0:
            return Response({'error': 'Aún no has tomado ningún punto.'}, status=400)
        if puntos_usados < total and not request.data.get('parcial'):
            return Response(
                {'error': f'Faltan puntos por tomar ({puntos_usados} de {total}).'},
                status=409,
            )
        prom = tomados.aggregate(**{c: Avg(c) for c in CAMPOS_SENSOR})
        for campo in CAMPOS_SENSOR:
            if prom[campo] is None:
                return Response(
                    {'error': f'Los puntos tomados no tienen valor de {campo}.'},
                    status=400,
                )
            valores[campo] = round(float(prom[campo]), 2)
    else:
        datos = request.data.get('datos') or {}
        puntos_usados = 1
        for campo in CAMPOS_SENSOR:
            try:
                valores[campo] = round(float(datos.get(campo)), 2)
            except (TypeError, ValueError, AttributeError):
                return Response(
                    {'error': f'Valor inválido o faltante: {campo}.'}, status=400
                )

    preferencia = s.cultivo_deseado
    if preferencia == 'No especificado':
        preferencia = ''

    diagnostico = calcular_diagnostico_edafologico(
        valores['humedad'], valores['temperatura'], valores['conductividad'],
        valores['ph'], valores['nitrogeno'], valores['fosforo'], valores['potasio'],
        preferencia=preferencia,
    )

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