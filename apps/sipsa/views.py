from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
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

    # Datos para Chart.js
    labels = [p.semana_label for p in precios]
    valores = [float(p.precio_kg) for p in precios]

    return render(request, 'sipsa/detalle_cultivo.html', {
        'cultivo': cultivo,
        'precios': precios,
        'prediccion': pred,
        'chart_labels': labels,
        'chart_valores': valores,
    })


@login_required
def actualizar_precios_view(request):
    """POST → llama actualizar_sipsa y devuelve JSON."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
    try:
        out = StringIO()
        call_command('actualizar_sipsa', stdout=out)
        return JsonResponse({'status': 'ok', 'message': 'Precios SIPSA actualizados correctamente.'})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)
