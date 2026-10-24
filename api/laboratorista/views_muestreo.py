import json

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsLaboratorista
from apps.analisis.models import PuntoMuestreo
from apps.sensores.views import captura_estable
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