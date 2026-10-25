"""
Enrutamiento URL para la Aplicación de Cultivos.
==============================================
Define los patrones de ruta para la entrega del catálogo offline consumido
por la PWA y los clientes web tradicionales.
"""

from django.urls import path
from . import views

# Espacio de nombres de la aplicación para resolución reversa (cultivos:api_catalogo_offline)
app_name = 'cultivos'

urlpatterns = [
    # Endpoint de descarga del catálogo maestro de cultivos para Dexie.js / IndexedDB
    path('api/catalogo-offline/', views.api_catalogo_offline, name='api_catalogo_offline'),
]
