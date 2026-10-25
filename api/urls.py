"""
Enrutador Principal de la API REST (Versión 1) - TierSystem.
Organiza los namespaces para los clientes móviles (Flutter) y herramientas externas,
exponiendo el esquema OpenAPI 3.0 autogenerado y la interfaz Swagger UI.
"""

from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Generación dinámica del esquema OpenAPI 3.0 en formato YAML/JSON
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    # Interfaz gráfica interactiva Swagger UI para pruebas y documentación viva
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),

    # Autenticación sin estado basada en JWT: Login, Refresh Token, Registro y Sesión activa
    path('auth/', include('api.auth.urls')),

    # Servicios dedicados al portal móvil del agricultor (fincas, estudios, mercado y perfil)
    path('agricultor/', include('api.agricultor.urls')),

    # Servicios de campo para el técnico/laboratorista (banco de órdenes, muestreo IoT y reportes)
    path('laboratorista/', include('api.laboratorista.urls')),

    # Enrutamiento de compatibilidad retroactiva para endpoints móviles previos
    path('', include('api.agricultor.urls')),
]