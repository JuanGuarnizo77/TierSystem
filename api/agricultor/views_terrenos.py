"""
Controlador de Gestión de Predios Agrícolas (Fincas) - Perfil Agricultor API.
Provee operaciones CRUD completas sobre el modelo Terreno, aislando estrictamente
los predios por productor y garantizando la asignación automática del propietario.
"""

from rest_framework import viewsets

from apps.terrenos.models import Terreno
from api.permissions import IsAgricultor
from .serializers import TerrenoSerializer


class TerrenoViewSet(viewsets.ModelViewSet):
    """
    ViewSet REST para la gestión de predios del agricultor autenticado.
    Endpoints expuestos:
    - GET    /api/v1/agricultor/terrenos/        -> Lista ordenada de fincas registradas
    - POST   /api/v1/agricultor/terrenos/        -> Radica una nueva finca con GeoJSON y hectáreas
    - GET    /api/v1/agricultor/terrenos/<id>/   -> Consulta detallada de linderos y cultivo
    - PUT    /api/v1/agricultor/terrenos/<id>/   -> Actualización total del predio
    - PATCH  /api/v1/agricultor/terrenos/<id>/   -> Actualización parcial de atributos
    - DELETE /api/v1/agricultor/terrenos/<id>/   -> Eliminación física del registro de finca
    """
    serializer_class = TerrenoSerializer
    permission_classes = [IsAgricultor]

    def get_queryset(self):
        """
        Aislamiento multi-inquilino (Multi-tenant):
        Filtra rigurosamente los predios en base de datos para que cada agricultor
        únicamente tenga visibilidad y control sobre sus propias tierras.
        """
        return Terreno.objects.filter(
            agricultor=self.request.user
        ).order_by('-fecha_registro')

    def perform_create(self, serializer):
        """
        Sobrescribe el guardado para asociar de manera transparente y forzada
        al usuario autenticado en la sesión/token como titular legal de la finca.
        """
        serializer.save(agricultor=self.request.user)

