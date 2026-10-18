from rest_framework import mixins, viewsets
from rest_framework.response import Response

from apps.solicitudes.models import SolicitudAnalisis
from api.permissions import IsAgricultor
from .serializers import SolicitudSerializer

ESTADOS_ACTIVOS = ['PENDIENTE', 'ASIGNADA', 'EN_PROCESO']


class SolicitudViewSet(mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """
    Gestión de solicitudes de análisis para el agricultor autenticado.
    GET    /api/v1/agricultor/solicitudes/        -> lista las solicitudes
    POST   /api/v1/agricultor/solicitudes/        -> crea una solicitud (máximo una activa)
    GET    /api/v1/agricultor/solicitudes/<id>/   -> detalle
    DELETE /api/v1/agricultor/solicitudes/<id>/   -> cancela (solo si está PENDIENTE)
    """
    serializer_class = SolicitudSerializer
    permission_classes = [IsAgricultor]

    def get_queryset(self):
        return (SolicitudAnalisis.objects
                .filter(agricultor=self.request.user)
                .select_related('terreno', 'analisis_resultado')
                .order_by('-fecha_solicitud'))

    def create(self, request, *args, **kwargs):
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
        serializer.save(agricultor=self.request.user, estado='PENDIENTE')

    def destroy(self, request, *args, **kwargs):
        solicitud = self.get_object()
        if solicitud.estado != 'PENDIENTE':
            return Response(
                {'error': 'Solo se pueden cancelar solicitudes en estado Pendiente.'},
                status=400,
            )
        solicitud.delete()
        return Response(status=204)
