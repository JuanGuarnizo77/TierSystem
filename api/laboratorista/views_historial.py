"""
Controlador de Historial y Consulta de Resultados - Perfil Laboratorista API.
Permite auditar los análisis edafológicos culminados por el técnico y reconstruir
el reporte agronómico con semaforización de nutrientes y cultivos viables recomendados.
"""

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.agricultor.views_resultados import _resumen
from api.permissions import IsLaboratorista
from apps.analisis.models import RegistroAnalisis
from apps.solicitudes.models import SolicitudAnalisis
from apps.solicitudes.views import _evaluar_parametros_agronomicos


def _nombre(user):
    """Retorna el nombre formal del usuario o su nombre de cuenta como alternativa."""
    return user.get_full_name() or user.username


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def historial_view(request):
    """
    GET /api/v1/laboratorista/historial/
    Retorna la lista cronológica descendente de análisis culminados por el laboratorista.
    Cada elemento incluye la identificación del agricultor, predio, fecha y lecturas NPK/pH.
    """
    # Consulta optimizada precargando terreno y agricultor para eliminar consultas redundantes
    registros = (
        RegistroAnalisis.objects
        .filter(solicitud__laboratorista_asignado=request.user)
        .select_related('solicitud__terreno', 'solicitud__agricultor')
        .order_by('-fecha_analisis')
    )

    lista = []
    for r in registros:
        s = r.solicitud
        # Evalúa los parámetros agronómicos frente a los umbrales del cultivo deseado
        ev = _evaluar_parametros_agronomicos(r, s.cultivo_deseado)
        item = _resumen(s, ev)
        # Agrega las mediciones químicas exactas de laboratorio al resumen
        item.update({
            'agricultor': _nombre(s.agricultor),
            'fecha_analisis': r.fecha_analisis.isoformat(),
            'humedad': float(r.humedad),
            'ph': float(r.ph),
            'nitrogeno': float(r.nitrogeno),
            'fosforo': float(r.fosforo),
            'potasio': float(r.potasio),
        })
        lista.append(item)
    return Response(lista)


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def resultado_view(request, solicitud_id):
    """
    GET /api/v1/laboratorista/resultados/<solicitud_id>/
    Retorna el informe agronómico exhaustivo de un análisis de suelo finalizado:
    - Semáforo de nutrientes (bajo, óptimo, alto)
    - Recomendaciones de fertilización y enmiendas de acidez
    - Ranking de cultivos alternativos compatibles con el suelo
    - Consejo agronómico global generado por el motor dual
    """
    # Garantiza que el informe pertenezca a una orden asignada al técnico que consulta
    s = get_object_or_404(
        SolicitudAnalisis,
        id=solicitud_id,
        laboratorista_asignado=request.user,
    )
    if not hasattr(s, 'analisis_resultado'):
        return Response({'error': 'Esta solicitud aún no tiene análisis.'}, status=404)

    # Computa la matriz de compatibilidad y enmiendas
    ev = _evaluar_parametros_agronomicos(s.analisis_resultado, s.cultivo_deseado)
    data = _resumen(s, ev)
    data.update({
        'agricultor': _nombre(s.agricultor),
        'laboratorista': _nombre(request.user),
        'fecha_analisis': s.analisis_resultado.fecha_analisis.isoformat(),
        'parametros': ev['parametros'],
        'recomendaciones': ev['recomendaciones'],
        'cultivos_alternativos': ev['cultivos_alternativos'],
        'consejo_general': ev['consejo_general'],
    })
    return Response(data)