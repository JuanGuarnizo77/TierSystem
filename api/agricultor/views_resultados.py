from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.solicitudes.models import SolicitudAnalisis
from apps.solicitudes.views import _evaluar_parametros_agronomicos
from api.permissions import IsAgricultor


def _resumen(s, ev):
    return {
        'id': s.id,
        'terreno_nombre': s.terreno.nombre,
        'cultivo': s.cultivo_deseado,
        'modalidad_texto': s.get_modalidad_display(),
        'fecha': s.fecha_solicitud.isoformat(),
        'compatibilidad': ev['compatibilidad'],
        'nivel': ev['nivel_compatibilidad'],
        'color': ev['color_compatibilidad'],
    }


def _completadas(user):
    return (SolicitudAnalisis.objects
            .filter(agricultor=user, estado='COMPLETADA')
            .select_related('analisis_resultado', 'terreno')
            .order_by('-fecha_solicitud'))


@api_view(['GET'])
@permission_classes([IsAgricultor])
def historial_view(request):
    """GET /api/v1/agricultor/historial/ -> análisis completados."""
    lista = []
    for s in _completadas(request.user):
        if hasattr(s, 'analisis_resultado'):
            ev = _evaluar_parametros_agronomicos(s.analisis_resultado, s.cultivo_deseado)
            lista.append(_resumen(s, ev))
    return Response(lista)


@api_view(['GET'])
@permission_classes([IsAgricultor])
def resultado_view(request, solicitud_id):
    """GET /api/v1/agricultor/resultados/<id>/ -> reporte completo."""
    s = get_object_or_404(SolicitudAnalisis, id=solicitud_id, agricultor=request.user)
    if not hasattr(s, 'analisis_resultado'):
        return Response({'error': 'Esta solicitud aún no tiene análisis.'}, status=404)
    ev = _evaluar_parametros_agronomicos(s.analisis_resultado, s.cultivo_deseado)
    data = _resumen(s, ev)
    data.update({
        'laboratorista': (s.laboratorista_asignado.get_full_name() or s.laboratorista_asignado.username)
        if s.laboratorista_asignado else None,
        'fecha_analisis': s.analisis_resultado.fecha_analisis.isoformat(),
        'parametros': ev['parametros'],
        'recomendaciones': ev['recomendaciones'],
        'cultivos_alternativos': ev['cultivos_alternativos'],
        'consejo_general': ev['consejo_general'],
    })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAgricultor])
def comparar_view(request):
    """GET /api/v1/agricultor/comparar/?id1=..&id2=.. (sin ids: los 2 más recientes)."""
    disponibles = [s for s in _completadas(request.user) if hasattr(s, 'analisis_resultado')]
    if len(disponibles) < 2:
        return Response({'error': 'Necesitas al menos 2 análisis completados para comparar.'}, status=400)

    id1 = request.query_params.get('id1') or disponibles[0].id
    id2 = request.query_params.get('id2') or disponibles[1].id
    s1 = get_object_or_404(SolicitudAnalisis, id=id1, agricultor=request.user)
    s2 = get_object_or_404(SolicitudAnalisis, id=id2, agricultor=request.user)
    if not hasattr(s1, 'analisis_resultado') or not hasattr(s2, 'analisis_resultado'):
        return Response({'error': 'Una solicitud no tiene análisis completado.'}, status=400)

    ev1 = _evaluar_parametros_agronomicos(s1.analisis_resultado, s1.cultivo_deseado)
    ev2 = _evaluar_parametros_agronomicos(s2.analisis_resultado, s2.cultivo_deseado)

    filas = []
    for p1 in ev1['parametros']:
        p2 = next((p for p in ev2['parametros'] if p['nombre'] == p1['nombre']), None)
        if p2:
            filas.append({
                'parametro': p1['nombre'],
                'unidad': p1['unidad'],
                'ideal': p1['ideal'],
                'val1': p1['medido'], 'estado1': p1['estado'],
                'val2': p2['medido'], 'estado2': p2['estado'],
                'diferencia': round(p1['medido'] - p2['medido'], 2),
            })

    return Response({
        'disponibles': [_resumen(s, _evaluar_parametros_agronomicos(s.analisis_resultado, s.cultivo_deseado))
                        for s in disponibles],
        'a': _resumen(s1, ev1),
        'b': _resumen(s2, ev2),
        'diferencia_compatibilidad': ev1['compatibilidad'] - ev2['compatibilidad'],
        'filas': filas,
    })