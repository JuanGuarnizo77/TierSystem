"""
Controladores Web y API para Monitoreo de Precios SIPSA y Proyecciones de Mercado.
==================================================================================
Proporciona vistas de visualización de series de tiempo y endpoints JSON:
  1. `dashboard`: Tablero principal con lista de cultivos, última cotización oficial
     y proyección econométrica calculada en tiempo real.
  2. `detalle_cultivo`: Ficha histórica detallada con gráfico interactivo (Chart.js)
     y desglose estadístico.
  3. `api_json`: Endpoint REST para clientes móviles y PWA con la serie de precios.
  4. `actualizar_precios_view`: Disparador administrativo para ejecutar el comando
     de sincronización `actualizar_sipsa`.
"""

import json
from types import SimpleNamespace
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.core.management import call_command
from io import StringIO

from apps.cultivos.models import Cultivo
from .models import PrecioSemanal
from .prediccion import calcular_prediccion


def _obtener_prediccion_cultivo(precios_hist):
    """
    Función utilitaria que computa la regresión lineal sobre una serie histórica de precios.

    Parámetros:
        precios_hist (List[PrecioSemanal]): Registros ordenados cronológicamente.

    Retorna:
        SimpleNamespace|None: Objeto con atributos de tendencia, confianza, precio y variación.
    """
    if not precios_hist or len(precios_hist) < 3:
        return None

    valores = [float(p.precio_kg) for p in precios_hist]
    pred = calcular_prediccion(valores)

    return SimpleNamespace(
        tendencia_predicha=pred.get('tendencia', 'Estable'),
        confianza_pct=pred.get('confianza_pct', 0.0),
        precio_estimado=pred.get('precio_estimado'),
        variacion_estimada_pct=pred.get('variacion_pct', 0.0),
        semanas_usadas=pred.get('semanas_usadas', len(valores)),
    )


@login_required
def dashboard(request):
    """
    Vista de panel principal de cotizaciones agropecuarias SIPSA.

    Optimización:
      - Aplica `prefetch_related('precios_semanales')` sobre cultivos activos para
        cargar el histórico completo en una única consulta adicional.
      - Itera sobre cada especie calculando la tendencia mediante `_obtener_prediccion_cultivo`.
      - Identifica la marca temporal más reciente de actualización en el sistema.
    """
    cultivos = Cultivo.objects.filter(activo=True).prefetch_related('precios_semanales')

    tabla = []
    for c in cultivos:
        precios_hist = list(c.precios_semanales.order_by('fecha_semana'))
        ultimo = precios_hist[-1] if precios_hist else None
        pred = _obtener_prediccion_cultivo(precios_hist)
        tabla.append({
            'cultivo': c,
            'ultimo_precio': ultimo,
            'prediccion': pred,
            'ultima_fecha': precios_hist[-1].fecha_semana.strftime('%d/%m/%Y') if precios_hist else '—',
        })

    ultima_actualizacion = (
        PrecioSemanal.objects.order_by('-fecha_registro').first()
    )

    return render(request, 'sipsa/dashboard.html', {
        'tabla': tabla,
        'ultima_actualizacion': ultima_actualizacion.fecha_registro if ultima_actualizacion else None,
        'total_cultivos': len(tabla),
    })


@login_required
def detalle_cultivo(request, cultivo_id):
    """
    Vista detallada de la serie histórica y proyección para un cultivo.

    Prepara los datos estructurados en formato JSON para la renderización de la
    curva temporal mediante librerías gráficas de frontend (Chart.js / ApexCharts).
    """
    cultivo = get_object_or_404(Cultivo, pk=cultivo_id, activo=True)
    precios_qs = cultivo.precios_semanales.order_by('fecha_semana')
    precios_list = list(precios_qs)
    pred = _obtener_prediccion_cultivo(precios_list)

    labels = [p.fecha_semana.strftime('%d/%m/%Y') for p in precios_list]
    valores = [float(p.precio_kg) for p in precios_list]

    return render(request, 'sipsa/detalle_cultivo.html', {
        'cultivo': cultivo,
        'precios': precios_list,
        'prediccion': pred,
        'chart_labels': json.dumps(labels),
        'chart_valores': json.dumps(valores),
    })


@login_required
def api_json(request, cultivo_id):
    """
    Endpoint JSON: GET /sipsa/cultivo/<cultivo_id>/api/
    --------------------------------------------------
    Proporciona la serie temporal de precios y la predicción econométrica a clientes REST.
    """
    cultivo = get_object_or_404(Cultivo, pk=cultivo_id, activo=True)
    precios_qs = cultivo.precios_semanales.order_by('fecha_semana')
    precios_list = list(precios_qs)

    precios_data = [
        {
            'semana': p.semana_label,
            'fecha': p.fecha_semana.isoformat(),
            'precio_kg': float(p.precio_kg),
            'precio_local': float(p.precio_local) if p.precio_local is not None else None,
        }
        for p in precios_list
    ]

    pred = _obtener_prediccion_cultivo(precios_list)
    prediccion_data = None
    if pred:
        prediccion_data = {
            'tendencia': pred.tendencia_predicha,
            'confianza_pct': pred.confianza_pct,
            'precio_estimado': float(pred.precio_estimado) if pred.precio_estimado is not None else None,
            'variacion_estimada_pct': pred.variacion_estimada_pct,
            'semanas_usadas': pred.semanas_usadas,
        }

    return JsonResponse({
        'cultivo': {
            'id': cultivo.pk,
            'nombre': cultivo.nombre,
            'unidad': getattr(cultivo, 'unidad', 'kg'),
        },
        'precios': precios_data,
        'prediccion': prediccion_data,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/agricultor/sipsa/')
def actualizar_precios_view(request):
    """
    Endpoint de gestión administrativa: POST /sipsa/actualizar/
    -----------------------------------------------------------
    Ejecuta el comando `actualizar_sipsa` bajo demanda.
    Restringido exclusivamente a superusuarios (`is_superuser=True`).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
    try:
        out = StringIO()
        call_command('actualizar_sipsa', stdout=out)
        return JsonResponse({'status': 'ok', 'message': 'Precios SIPSA actualizados correctamente.'})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)
