"""
Procesadores de Contexto Globales para Plantillas HTML de Django.
==================================================================
Inyecta variables transversales en el contexto de renderizado de todas las
plantillas del proyecto, optimizando la experiencia de usuario y la navegación.
"""

from apps.solicitudes.models import SolicitudAnalisis


def solicitud_activa(request):
    """
    Inyecta el indicador booleano `solicitud_activa_sidebar` en el contexto global.

    Regla de Negocio (US-0009):
      Si el usuario autenticado tiene rol 'AGRICULTOR', verifica si posee una solicitud
      en curso ('PENDIENTE', 'ASIGNADA' o 'EN_PROCESO').

    Efecto en la interfaz:
      Permite al menú lateral (sidebar) deshabilitar o alertar visualmente el botón
      de "Nueva Solicitud" para evitar infracciones de la regla de solicitud única activa.
    """
    if request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.rol == 'AGRICULTOR':
        activa = SolicitudAnalisis.objects.filter(
            agricultor=request.user,
            estado__in=['PENDIENTE', 'ASIGNADA', 'EN_PROCESO']
        ).exists()
        return {'solicitud_activa_sidebar': activa}
    return {'solicitud_activa_sidebar': False}
