# api/urls.py
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Schema y documentación interactiva Swagger
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),

    # Módulo de Autenticación JWT (login, refresh, me, registro, logout)
    path('auth/', include('api.auth.urls')),

    # Módulo de Agricultor (fincas, solicitudes y perfil)
    path('agricultor/', include('api.agricultor.urls')),

    # Módulo de Laboratorista
    path('laboratorista/', include('api.laboratorista.urls')),

    # Alias directo para compatibilidad con llamadas existentes
    path('', include('api.agricultor.urls')),
]