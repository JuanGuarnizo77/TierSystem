from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAgricultor
from apps.cultivos.models import Cultivo


@api_view(['GET'])
@permission_classes([IsAgricultor])
def catalogo_cultivos_view(request):
    """GET /api/v1/agricultor/cultivos/ -> catálogo completo de cultivos del Huila desde base de datos MySQL."""
    cultivos = Cultivo.objects.filter(activo=True).order_by('nombre')
    return Response([c.to_catalogo_dict() for c in cultivos])