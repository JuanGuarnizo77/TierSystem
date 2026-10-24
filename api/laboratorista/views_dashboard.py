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
    Devuelve los contadores del panel del laboratorista.
    """
    user = request.user

    total_pendientes = SolicitudAnalisis.objects.filter(
        estado='PENDIENTE'
    ).count()

    total_completados = RegistroAnalisis.objects.filter(
        solicitud__laboratorista_asignado=user
    ).count()

    return Response({
        'nombre': user.get_full_name() or user.username,
        'total_pendientes': total_pendientes,
        'total_completados': total_completados,
    })