"""
Controlador de Gestión de Solicitudes de Análisis de Suelo - Perfil Agricultor API.
Implementa el ciclo de vida de peticiones agronómicas desde la app móvil:
- Radicación con validación de exclusividad activa (Regla de negocio US-0009).
- Consulta histórica de estados (PENDIENTE, ASIGNADA, EN_PROCESO, COMPLETADA).
- Cancelación controlada (restringida únicamente al estado inicial PENDIENTE).
"""

from rest_framework import mixins, viewsets
from rest_framework.response import Response

from apps.solicitudes.models import SolicitudAnalisis
from api.permissions import IsAgricultor
from .serializers import SolicitudSerializer

# Estados que configuran un trámite operativo abierto e impiden radicar duplicados concurrentes
ESTADOS_ACTIVOS = ['PENDIENTE', 'ASIGNADA', 'EN_PROCESO']


class SolicitudViewSet(mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """
    ViewSet REST para el seguimiento de órdenes de estudio de suelos.
    Endpoints expuestos:
    - GET    /api/v1/agricultor/solicitudes/        -> Lista ordenada de solicitudes del productor
    - POST   /api/v1/agricultor/solicitudes/        -> Radica una nueva orden (aplica regla US-0009)
    - GET    /api/v1/agricultor/solicitudes/<id>/   -> Consulta detallada del estado y visita técnica
    - DELETE /api/v1/agricultor/solicitudes/<id>/   -> Anulación controlada si aún no fue asignada
    """
    serializer_class = SolicitudSerializer
    permission_classes = [IsAgricultor]

    def get_queryset(self):
        """
        Consulta optimizada con select_related():
        Precarga en un único JOIN el terreno asociado y el resultado del análisis
        para evitar latencia en la pantalla de seguimiento del agricultor.
        """
        return (SolicitudAnalisis.objects
                .filter(agricultor=self.request.user)
                .select_related('terreno', 'analisis_resultado')
                .order_by('-fecha_solicitud'))

    def create(self, request, *args, **kwargs):
        """
        Sobrescribe la creación para hacer cumplir la Regla de Negocio US-0009:
        Un productor no puede tener más de una orden en curso de manera simultánea.
        Debe aguardar la finalización de la actual o cancelarla si sigue pendiente.
        """
        activa = SolicitudAnalisis.objects.filter(
            agricultor=request.user, estado__in=ESTADOS_ACTIVOS
        ).exists()
        if activa:
            return Response(
                {'error': 'Ya tienes una solicitud activa. Debes esperar a que finalice o cancelarla.'},
                status=400,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Asigna de forma obligatoria al usuario en sesión y el estado inicial PENDIENTE."""
        serializer.save(agricultor=self.request.user, estado='PENDIENTE')

    def destroy(self, request, *args, **kwargs):
        """
        Permite la anulación de la orden únicamente si aún se encuentra en estado 'PENDIENTE'.
        Si la visita ya fue ASIGNADA a un laboratorista o se encuentra EN_PROCESO,
        se bloquea la eliminación para preservar la integridad operativa del técnico de campo.
        """
        solicitud = self.get_object()
        if solicitud.estado != 'PENDIENTE':
            return Response(
                {'error': 'Solo se pueden cancelar solicitudes en estado Pendiente.'},
                status=400,
            )
        solicitud.delete()
        return Response(status=204)

