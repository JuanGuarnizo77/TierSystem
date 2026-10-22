from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAgricultor
from core.cultivos_data import CULTIVOS_HUILA


@api_view(['GET'])
@permission_classes([IsAgricultor])
def catalogo_cultivos_view(request):
    """GET /api/v1/agricultor/cultivos/ -> catálogo completo de cultivos del Huila."""
    return Response(CULTIVOS_HUILA)