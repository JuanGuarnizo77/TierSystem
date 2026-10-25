"""
Enrutamiento URL para el Módulo de Precios SIPSA y Analítica de Mercado.
========================================================================
Define los patrones de ruta para el monitoreo de cotizaciones oficiales:
  - Dashboard consolidado de cultivos y tendencias (`dashboard`).
  - Vista individual de serie de tiempo con gráficos (`detalle_cultivo`).
  - Endpoint REST serializado (`api_json`).
  - Disparador de sincronización administrativa (`actualizar_precios`).
"""

from django.urls import path
from . import views

# Espacio de nombres de la aplicación para resolución reversa (sipsa:dashboard, etc.)
app_name = 'sipsa'

urlpatterns = [
    # Tablero principal de cotizaciones agropecuarias
    path('', views.dashboard, name='dashboard'),

    # Vista detallada de histórico y proyección para un cultivo
    path('cultivo/<int:cultivo_id>/', views.detalle_cultivo, name='detalle_cultivo'),

    # API JSON para consumo de frontend y clientes móviles
    path('cultivo/<int:cultivo_id>/api/', views.api_json, name='api_json'),

    # Disparador administrativo de ingesta y actualización de datos SIPSA
    path('actualizar/', views.actualizar_precios_view, name='actualizar_precios'),
]
