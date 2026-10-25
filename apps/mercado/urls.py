"""
Enrutamiento URL para el Módulo de Mercado y Comercialización Agrícola.
======================================================================
Define las rutas para el análisis de precios regionales, directorio de compradores,
actualización de cotizaciones bajo demanda y vitrina de productos del agricultor.
"""

from django.urls import path
from . import views

# Espacio de nombres de la aplicación para resolución reversa (mercado:precios_sipsa, etc.)
app_name = 'mercado'

urlpatterns = [
    # Vista principal de precios regionales y cotizaciones de referencia
    path('', views.precios_sipsa, name='precios_sipsa'),

    # Listado de productos agropecuarios publicados
    path('productos/', views.listado_productos, name='listado_productos'),

    # Endpoint JSON para cambio dinámico de cultivo en la interfaz AJAX
    path('api/cultivo/<str:cultivo_nombre>/', views.api_datos_cultivo_mercado, name='api_datos_cultivo'),

    # Gestión de catálogo del productor (vitrina comercial)
    path('mi-tienda/', views.mi_tienda, name='mi_tienda'),
    path('agregar-producto/', views.agregar_producto, name='agregar_producto'),
    path('eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),

    # Sincronización manual de cotizaciones mediante llamada al comando interno
    path('actualizar/', views.actualizar_precios_view, name='actualizar_precios'),
]
