from rest_framework import viewsets

from apps.terrenos.models import Terreno
from api.permissions import IsAgricultor
from .serializers import TerrenoSerializer


class TerrenoViewSet(viewsets.ModelViewSet):
    """
    CRUD de Fincas / Terrenos para el agricultor autenticado.
    GET    /api/v1/agricultor/terrenos/        -> lista las fincas
    POST   /api/v1/agricultor/terrenos/        -> crea una finca
    GET    /api/v1/agricultor/terrenos/<id>/   -> detalle
    PUT    /api/v1/agricultor/terrenos/<id>/   -> edita
    DELETE /api/v1/agricultor/terrenos/<id>/   -> elimina
    """
    serializer_class = TerrenoSerializer
    permission_classes = [IsAgricultor]

    def get_queryset(self):
        return Terreno.objects.filter(
            agricultor=self.request.user
        ).order_by('-fecha_registro')

    def perform_create(self, serializer):
        serializer.save(agricultor=self.request.user)
