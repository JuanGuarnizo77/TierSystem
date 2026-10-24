from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAgricultor
from apps.sipsa.models import PrecioSemanal
from apps.mercado.views import (
    DATOS_MERCADO_HUILA,
    _normalizar_tendencia,
    _get_compradores_for_cultivo,
)


@api_view(['GET'])
@permission_classes([IsAgricultor])
def precios_sipsa_view(request):
    """GET /api/v1/agricultor/mercado/precios/ -> precios SIPSA por cultivo + estado de conexión."""
    ahora = timezone.now()

    ps_reciente = PrecioSemanal.objects.order_by('-fecha_registro').first()
    ultima_global = None
    if ps_reciente and ps_reciente.fecha_registro:
        ts = ps_reciente.fecha_registro
        dias = (ahora - ts).days
        ultima_global = timezone.localtime(ts).strftime("%d/%m/%Y %H:%M")
        if ts >= ahora - timedelta(hours=24):
            estado = 'online'
            mensaje = f"Precios actualizados al {ultima_global} desde SIPSA/DANE."
        elif ts >= ahora - timedelta(hours=72):
            estado = 'reciente'
            mensaje = f"Precios con {dias} día(s) de antigüedad. Se recomienda actualizar."
        else:
            estado = 'desactualizado'
            mensaje = f"Precios con más de 72h de antigüedad ({dias} días). Mostrando datos de referencia."
    else:
        estado = 'reciente'
        mensaje = "Mostrando precios oficiales y de referencia regional Huila."

    nombres = list(DATOS_MERCADO_HUILA.keys())
    tabla = []
    for nombre in nombres:
        d = DATOS_MERCADO_HUILA.get(nombre, {})
        if d:
            tabla.append({
                'cultivo': nombre,
                'precio_promedio': d.get('precio_promedio', 0),
                'precio_local': d.get('precio_local', d.get('precio_promedio', 0)),
                'unidad': d.get('unidad', 'kg'),
                'tendencia': _normalizar_tendencia(d.get('tendencia', 'Estable')),
                'variacion_porcentaje': float(
                    str(d.get('variacion', '0%')).replace('%', '').replace('+', '')
                ),
                'fuente': d.get('fuente', 'SIPSA / DANE'),
                'ultima_actualizacion': '—',
                'dias_desde_actualizacion': None,
                'compradores': _get_compradores_for_cultivo(nombre),
                'historial': d.get('historial', []),
            })

    return Response({
        'estado_conexion': estado,
        'mensaje_conexion': mensaje,
        'ultima_actualizacion_global': ultima_global,
        'fecha_hoy': timezone.localtime(ahora).strftime("%d/%m/%Y"),
        'precios': tabla,
    })


@api_view(['POST'])
@permission_classes([IsAgricultor])
def actualizar_precios_view(request):
    """POST /api/v1/agricultor/mercado/actualizar/ -> ejecuta el comando actualizar_sipsa."""
    out = StringIO()
    try:
        call_command('actualizar_sipsa', stdout=out)
        return Response({'status': 'ok', 'output': out.getvalue()})
    except Exception as exc:
        return Response({'status': 'error', 'error': str(exc)}, status=500)