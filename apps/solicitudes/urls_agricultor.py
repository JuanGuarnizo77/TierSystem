"""
Enrutamiento URL de Solicitudes y Resultados para el Rol Agricultor.
===================================================================
Define los endpoints web para el productor agropecuario:
  - Creación, consulta y cancelación de solicitudes (US-0009, US-0010).
  - Consulta detallada de resultados edáficos y comparativas (US-0011, US-0028).
  - Generación de reportes descargables en formatos PDF y Excel (.xlsx) (US-0012).
"""

from django.urls import path
from . import views

# Espacio de nombres para agricultores (solicitudes_agricultor:crear_solicitud, etc.)
app_name = 'solicitudes_agricultor'

urlpatterns = [
    # Monitoreo y creación de solicitudes
    path('mis-solicitudes/', views.mis_solicitudes_agricultor, name='mis_solicitudes'),
    path('crear/', views.crear_solicitud, name='crear_solicitud'),
    path('cancelar/<int:solicitud_id>/', views.cancelar_solicitud, name='cancelar_solicitud'),

    # Análisis agronómico, historial y comparativas
    path('historial/', views.historial_analisis_agricultor, name='historial'),
    path('comparar/', views.comparar_analisis_agricultor, name='comparar_analisis'),
    path('resultado/<int:solicitud_id>/', views.resultado_detalle_agricultor, name='resultado_detalle'),

    # Exportación masiva de historial (PDF y Excel)
    path('historial/exportar-pdf/', views.exportar_historial_pdf, name='exportar_historial_pdf'),
    path('historial/exportar-excel/', views.exportar_historial_excel, name='exportar_historial_excel'),

    # Exportación técnica individual de un análisis específico (PDF y Excel)
    path('resultado/<int:solicitud_id>/exportar-pdf/', views.exportar_analisis_individual_pdf, name='exportar_analisis_pdf'),
    path('resultado/<int:solicitud_id>/exportar-excel/', views.exportar_analisis_individual_excel, name='exportar_analisis_excel'),
]
