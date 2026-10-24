from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAgricultor
from apps.cultivos.models import Cultivo
from apps.sipsa.models import PrecioSemanal


def _pred_dict(pred):
    if not pred:
        return None
    return {
        'tendencia': pred.tendencia_predicha,
        'confianza_pct': pred.confianza_pct,
        'precio_estimado': float(pred.precio_estimado)
        if pred.precio_estimado is not None else None,
        'variacion_estimada_pct': pred.variacion_estimada_pct,
        'semanas_usadas': pred.semanas_usadas,
    }


@api_view(['GET'])
@permission_classes([IsAgricultor])
def reportes_lista_view(request):
    """
    GET /api/v1/agricultor/reportes/
    Lista de cultivos SIPSA con último precio y predicción.
    """
    cultivos = Cultivo.objects.filter(activo=True).prefetch_related(
        'precios_semanales', 'prediccion'
    )

    filas = []
    for c in cultivos:
        ultimo = c.precios_semanales.order_by('-fecha_semana').first()
        filas.append({
            'id': c.pk,
            'nombre': c.nombre,
            'categoria': c.categoria,
            'unidad': getattr(c, 'unidad', 'kg'),
            'ultimo_precio': float(ultimo.precio_kg) if ultimo else None,
            'semana': ultimo.semana_label if ultimo else None,
            'prediccion': _pred_dict(getattr(c, 'prediccion', None)),
        })

    ultima = PrecioSemanal.objects.order_by('-fecha_registro').first()
    return Response({
        'total': len(filas),
        'ultima_actualizacion': ultima.fecha_registro if ultima else None,
        'cultivos': filas,
    })


@api_view(['GET'])
@permission_classes([IsAgricultor])
def reportes_detalle_view(request, cultivo_id):
    """
    GET /api/v1/agricultor/reportes/<id>/
    Serie histórica semanal + predicción de un cultivo.
    """
    cultivo = get_object_or_404(Cultivo, pk=cultivo_id, activo=True)
    precios = cultivo.precios_semanales.order_by('fecha_semana')

    return Response({
        'cultivo': {
            'id': cultivo.pk,
            'nombre': cultivo.nombre,
            'categoria': cultivo.categoria,
            'unidad': getattr(cultivo, 'unidad', 'kg'),
        },
        'precios': [
            {
                'semana': p.semana_label,
                'fecha': p.fecha_semana.isoformat(),
                'precio_kg': float(p.precio_kg),
                'precio_local': float(p.precio_local)
                if p.precio_local is not None else None,
            }
            for p in precios
        ],
        'prediccion': _pred_dict(getattr(cultivo, 'prediccion', None)),
    })