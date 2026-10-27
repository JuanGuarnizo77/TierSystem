"""
Enrutamiento URL para el Módulo de Análisis de Laboratorio.
==========================================================
Define las rutas web de consulta de historial de análisis realizados.
"""

from django.urls import path
from . import views

# Espacio de nombres de la aplicación para resolución reversa (analisis:historial)
app_name = 'analisis'

urlpatterns = [
    # Vista web del registro histórico de análisis completados por el técnico
    path('historial/', views.historial_analisis, name='historial'),
]
