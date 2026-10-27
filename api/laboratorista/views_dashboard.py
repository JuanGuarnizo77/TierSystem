"""
Controlador del Panel Principal (Dashboard) del Laboratorista - TierSystem API.
Provee los contadores de solicitudes pendientes de asignación en el departamento
y el número de análisis completados satisfactoriamente por el laboratorista en sesión.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsLaboratorista
from apps.solicitudes.models import SolicitudAnalisis
from apps.analisis.models import RegistroAnalisis


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def dashboard_view(request):
    """
    GET /api/v1/laboratorista/dashboard/
    Retorna métricas clave para el técnico:
    - Nombre del funcionario
    - Total de solicitudes pendientes globales en espera de técnico
    - Total de análisis ejecutados por este usuario
    """
    user = request.user

    # Conteo optimizado en SQL (SELECT COUNT(*)) de solicitudes sin técnico asignado
    total_pendientes = SolicitudAnalisis.objects.filter(
        estado='PENDIENTE'
    ).count()

    # Conteo de estudios consolidados donde el técnico autenticado fue el responsable
    total_completados = RegistroAnalisis.objects.filter(
        solicitud__laboratorista_asignado=user
    ).count()

    # Estructura JSON para renderizado de tarjetas numéricas en Flutter
    return Response({
        'nombre': user.get_full_name() or user.username,
        'total_pendientes': total_pendientes,
        'total_completados': total_completados,
    })