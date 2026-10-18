from apps.solicitudes.models import SolicitudAnalisis

def solicitud_activa(request):
    if request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.rol == 'AGRICULTOR':
        activa = SolicitudAnalisis.objects.filter(
            agricultor=request.user,
            estado__in=['PENDIENTE', 'ASIGNADA', 'EN_PROCESO']
        ).exists()
        return {'solicitud_activa_sidebar': activa}
    return {'solicitud_activa_sidebar': False}
