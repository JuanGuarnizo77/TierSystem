"""
Módulo de Clases de Permisos Personalizados para Django REST Framework.
Controla el acceso granular a los endpoints de la API v1 según el rol
asignado en el perfil del usuario autenticado (AGRICULTOR, LABORATORISTA, ADMIN).
"""

from rest_framework.permissions import BasePermission


class IsAgricultor(BasePermission):
    """
    Filtro de autorización para endpoints exclusivos de productores agropecuarios.
    Verifica que la petición provenga de una sesión válida o token JWT activo
    y que el rol configurado en su perfil sea 'AGRICULTOR'.
    """
    message = "Acceso restringido: Se requieren permisos de perfil Agricultor para consultar este recurso."

    def has_permission(self, request, view):
        # Valida autenticación y existencia de perfil para prevenir fallos por AttributeError
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.rol == 'AGRICULTOR'
        )


class IsLaboratorista(BasePermission):
    """
    Filtro de autorización para técnicos y laboratoristas de campo.
    Protege las operaciones de captura de telemetría, gestión de órdenes de muestreo
    y consolidación de diagnósticos edafológicos.
    """
    message = "Acceso restringido: Se requieren credenciales técnicas de Laboratorista."

    def has_permission(self, request, view):
        # Comprueba que el usuario activo tenga asignado el rol operativo de campo
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.rol == 'LABORATORISTA'
        )


class IsAdmin(BasePermission):
    """
    Filtro de autorización con privilegios directivos y de auditoría.
    Permite acceso total a métricas globales, catálogos maestros y supervisión.
    """
    message = "Acceso restringido: Se requieren privilegios administrativos."

    def has_permission(self, request, view):
        # Verifica rol administrativo o superusuario de Django para tareas de mantenimiento
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                (hasattr(request.user, 'perfil') and request.user.perfil.rol == 'ADMIN')
                or request.user.is_superuser
            )
        )


class IsAgricultorOrAdmin(BasePermission):
    """
    Permiso híbrido para vistas compartidas entre el titular de la finca y el administrador.
    Útil en consultas de catálogos agronómicos, cotizaciones de mercado y reportes.
    """
    message = "Acceso restringido a Agricultores registrados o Administradores del sistema."

    def has_permission(self, request, view):
        # Valida que el rol corresponda a uno de los dos perfiles autorizados
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.rol in ('AGRICULTOR', 'ADMIN')
        )

