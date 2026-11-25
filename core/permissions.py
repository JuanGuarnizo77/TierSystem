"""
Módulo de Permisos y Decoradores Transversales de Seguridad.
===========================================================
Centraliza los decoradores y validaciones de autorización a nivel de vista
para el control de acceso basado en roles (RBAC) en la capa web tradicional,
aplicando el principio de mínimo privilegio y verificación estricta en servidor.

Para los permisos de la API REST Framework (JWT), referirse a `api.permissions`.
"""

from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse
from core.utils import registrar_evento_seguridad


def tiene_rol(user, *roles_permitidos):
    """
    Verifica de forma segura en el servidor si un usuario autenticado posee
    alguno de los roles especificados en su perfil (`AGRICULTOR`, `LABORATORISTA`, `ADMIN`).
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if 'ADMIN' in roles_permitidos and user.is_superuser:
        return True
    return bool(hasattr(user, 'perfil') and user.perfil.rol in roles_permitidos)


def rol_requerido(*roles_permitidos, es_json=False):
    """
    Decorador de control de acceso basado en roles (RBAC) para vistas basadas en funciones.

    - Si el usuario no está autenticado, redirige a 'login' (o retorna 401/403 en JSON).
    - Si el usuario no posee el rol requerido, registra el intento no autorizado
      en el log de seguridad y bloquea el acceso (403 JSON o redirección a 'home').
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if es_json:
                    return JsonResponse({'error': 'Autenticación requerida'}, status=401)
                return redirect('login')

            if not tiene_rol(request.user, *roles_permitidos):
                registrar_evento_seguridad(
                    'ACCESO_DENEGADO_ROL',
                    request=request,
                    nivel='WARNING',
                    detalle=f"Vista={view_func.__name__} requiere={roles_permitidos}",
                )
                if es_json:
                    return JsonResponse({'error': 'No autorizado'}, status=403)
                return redirect('home')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
