import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.core.management import call_command
from io import StringIO

from .models import CultivoSipsa, PrecioSemanal, PrediccionPrecio


@login_required
def dashboard(request):
    """Vista principal: tabla con todos los cultivos, último precio y predicción."""
    cultivos = CultivoSipsa.objects.filter(activo=True).prefetch_related(
        'precios_semanales', 'prediccion'
    )

    tabla = []
    for c in cultivos:
        ultimo = c.precios_semanales.order_by('-fecha_semana').first()
        pred = getattr(c, 'prediccion', None)
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
    """Detalle: serie histórica completa + gráfica + predicción."""
    cultivo = get_object_or_404(CultivoSipsa, pk=cultivo_id, activo=True)
    precios = cultivo.precios_semanales.order_by('fecha_semana')
    pred = getattr(cultivo, 'prediccion', None)

    # Serializar con json.dumps para garantizar JSON válido en Chart.js
    # (evita que Django use repr() de Python con comillas simples)
    labels = [p.semana_label for p in precios]
    valores = [float(p.precio_kg) for p in precios]

    return render(request, 'sipsa/detalle_cultivo.html', {
        'cultivo': cultivo,
        'precios': precios,
        'prediccion': pred,
        'chart_labels': json.dumps(labels),
        'chart_valores': json.dumps(valores),
    })


@login_required
def api_json(request, cultivo_id):
    """
    Devuelve JSON con la serie histórica de PrecioSemanal y la PrediccionPrecio
    del cultivo indicado. Consumido por Chart.js en detalle_cultivo.html y por
    clientes externos que quieran los datos brutos.

    GET /agricultor/sipsa/cultivo/<id>/api/
    Respuesta:
    {
      "cultivo": {"id": 1, "nombre": "...", "unidad": "kg"},
      "precios": [{"semana": "Sem 40-2026", "fecha": "2026-09-28", "precio_kg": 2650.0, "precio_local": 2570.5}, ...],
      "prediccion": {"tendencia": "Baja", "confianza_pct": 100.0, "precio_estimado": 2230.0, "variacion_estimada_pct": -1.33, "semanas_usadas": 8} | null
    }
    """
    cultivo = get_object_or_404(CultivoSipsa, pk=cultivo_id, activo=True)
    precios_qs = cultivo.precios_semanales.order_by('fecha_semana')

    precios_data = [
        {
            'semana': p.semana_label,
            'fecha': p.fecha_semana.isoformat(),
            'precio_kg': float(p.precio_kg),
            'precio_local': float(p.precio_local) if p.precio_local is not None else None,
        }
        for p in precios_qs
    ]

    pred = getattr(cultivo, 'prediccion', None)
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
            'unidad': cultivo.unidad,
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
