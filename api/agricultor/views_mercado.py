from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAgricultor
from apps.mercado.models import PrecioMercado
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

    # Estado de conexión (ventanas de 24 h y 72 h, igual que la web)
    pm_reciente = PrecioMercado.objects.order_by('-ultima_actualizacion').first()
    ultima_global = None
    if pm_reciente and pm_reciente.ultima_actualizacion:
        ts = pm_reciente.ultima_actualizacion
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
        estado = 'desactualizado'
        mensaje = "Sin datos recientes. Mostrando precios de referencia regional almacenados."

    # Tabla de precios (BD primero, diccionario estático como respaldo)
    nombres = list(dict.fromkeys(
        list(DATOS_MERCADO_HUILA.keys()) +
        list(PrecioMercado.objects.values_list('cultivo_nombre', flat=True).distinct())
    ))

    tabla = []
    for nombre in nombres:
        pm = PrecioMercado.objects.filter(cultivo_nombre=nombre).first()
        if pm:
            dias = (ahora - pm.ultima_actualizacion).days if pm.ultima_actualizacion else None
            tabla.append({
                'cultivo': pm.cultivo_nombre,
                'precio_promedio': float(pm.precio_promedio),
                'precio_local': float(pm.precio_local) if pm.precio_local else float(pm.precio_promedio),
                'unidad': pm.unidad,
                'tendencia': _normalizar_tendencia(pm.tendencia),
                'variacion_porcentaje': pm.variacion_porcentaje,
                'fuente': pm.fuente,
                'ultima_actualizacion': timezone.localtime(pm.ultima_actualizacion).strftime("%d/%m/%Y")
                if pm.ultima_actualizacion else '—',
                'dias_desde_actualizacion': dias,
                'compradores': _get_compradores_for_cultivo(pm.cultivo_nombre),
                'historial': DATOS_MERCADO_HUILA.get(pm.cultivo_nombre, {}).get(
                    'historial', [{'mes': 'Jun', 'precio': float(pm.precio_promedio)}]
                ),
            })
        else:
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
    """POST /api/v1/agricultor/mercado/actualizar/ -> ejecuta el comando actualizar_precios."""
    out = StringIO()
    try:
        call_command('actualizar_precios', stdout=out)
        return Response({'status': 'ok', 'output': out.getvalue()})
    except Exception as exc:
        return Response({'status': 'error', 'error': str(exc)}, status=500)