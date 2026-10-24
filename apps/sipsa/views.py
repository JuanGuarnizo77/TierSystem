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
    """Calcula la predicción dinámica de tendencia a partir de la serie de precios."""
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
    """Vista principal: tabla con todos los cultivos, último precio y predicción calculada al vuelo."""
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
    """Detalle: serie histórica completa + gráfica + predicción dinámica."""
    cultivo = get_object_or_404(Cultivo, pk=cultivo_id, activo=True)
    precios_qs = cultivo.precios_semanales.order_by('fecha_semana')
    precios_list = list(precios_qs)
    pred = _obtener_prediccion_cultivo(precios_list)

    labels = [p.semana_label for p in precios_list]
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
    Devuelve JSON con la serie histórica de PrecioSemanal y la predicción dinámica
    calculada del cultivo indicado.
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
    """POST → solo superusuarios; llama actualizar_sipsa y devuelve JSON."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
    try:
        out = StringIO()
        call_command('actualizar_sipsa', stdout=out)
        return JsonResponse({'status': 'ok', 'message': 'Precios SIPSA actualizados correctamente.'})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)
