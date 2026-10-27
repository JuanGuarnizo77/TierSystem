"""
Módulo de Vistas de Reportes de Mercado y Series Temporales para Agricultores.
=============================================================================
Expone endpoints REST para que los productores agrícolas consulten el monitoreo
de precios agropecuarios de la plataforma SIPSA/DANE y las proyecciones algorítmicas
de tendencia de precios (modelo de regresión y series de tiempo).

Permite a los productores tomar decisiones informadas de siembra basándose no solo
en la calidad del suelo sino también en la viabilidad económica y comercial en el Huila.
"""

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAgricultor
from apps.cultivos.models import Cultivo
from apps.sipsa.models import PrecioSemanal


def _pred_dict(pred):
    """
    Serializa el modelo de predicción económica a un diccionario estándar para la API.

    Parámetros:
        pred (PrediccionCultivo|None): Instancia con el resultado de la regresión o None.

    Retorna:
        dict|None: Métricas de tendencia ('ALZA', 'BAJA', 'ESTABLE'), porcentaje de
                   confianza estadística, precio proyectado a corto plazo y semanas analizadas.
    """
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
    --------------------------------
    Entrega el catálogo de cultivos agrícolas monitoreados por SIPSA junto con su
    cotización más reciente en plaza y la proyección económica vigente.

    Optimización:
      Utiliza `prefetch_related('precios_semanales', 'prediccion')` para evitar
      consultas adicionales a la base de datos al recorrer las relaciones de cada cultivo.

    Respuestas:
      - 200 OK: Total de cultivos, fecha de última ingesta global de SIPSA y lista de registros.
    """
    # Consulta masiva optimizada para precargar series de precios y predicciones
    cultivos = Cultivo.objects.filter(activo=True).prefetch_related(
        'precios_semanales', 'prediccion'
    )

    filas = []
    for c in cultivos:
        # Obtiene la cotización semanal más reciente registrada para este cultivo
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

    # Determina la marca temporal del registro más reciente en todo el sistema SIPSA
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
    -------------------------------------
    Proporciona la serie temporal histórica completa de precios y la predicción
    económica detallada para un cultivo específico.

    Diseñado para alimentar gráficos de línea y análisis de volatilidad en la aplicación móvil.

    Parámetros de URL:
      - cultivo_id (int): Identificador primario del cultivo a consultar.

    Respuestas:
      - 200 OK: Metadatos del cultivo, serie de precios ordenada cronológicamente y predicción.
      - 404 Not Found: Si el cultivo no existe o se encuentra inactivo.
    """
    # Validación de existencia del cultivo activo
    cultivo = get_object_or_404(Cultivo, pk=cultivo_id, activo=True)

    # Recuperación cronológica ascendente para representación directa en gráficos
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