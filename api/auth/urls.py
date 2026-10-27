"""
Rutas del Módulo de Autenticación JWT - TierSystem API.
Define los endpoints de inicio de sesión, renovación de tokens, perfil activo,
registro de productores y cierre de sesión para la aplicación móvil Flutter.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, me_view, registro_view, logout_view

urlpatterns = [
    # Inicio de sesión con credenciales: genera par de tokens access (8h) y refresh (30d)
    path('login/', LoginView.as_view(), name='api_login'),

    # Renovación de token de acceso expirado mediante refresh token
    path('refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),

    # Consulta de identidad y permisos del usuario actualmente autenticado
    path('me/', me_view, name='api_me'),

    # Registro de nuevos agricultores con expedición automática de sesión
    path('registro/', registro_view, name='api_registro'),

    # Cierre de sesión e invalidación del token en el cliente
    path('logout/', logout_view, name='api_logout'),
]

