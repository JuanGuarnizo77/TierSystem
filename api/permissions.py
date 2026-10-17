from rest_framework.permissions import BasePermission


class IsAgricultor(BasePermission):
    """Permite acceso solo a usuarios con rol AGRICULTOR."""
    message = "Solo los agricultores pueden acceder a este recurso."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.rol == 'AGRICULTOR'
        )


class IsLaboratorista(BasePermission):
    """Permite acceso solo a usuarios con rol LABORATORISTA."""
    message = "Solo los laboratoristas pueden acceder a este recurso."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.rol == 'LABORATORISTA'
        )


class IsAdmin(BasePermission):
    """Permite acceso solo a usuarios con rol ADMIN."""
    message = "Solo los administradores pueden acceder a este recurso."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.rol == 'ADMIN'
        )


class IsAgricultorOrAdmin(BasePermission):
    """Permite acceso a Agricultores y Admins."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.rol in ('AGRICULTOR', 'ADMIN')
        )
