from django.urls import path
from . import views

app_name = 'solicitudes_agricultor'

urlpatterns = [
    path('mis-solicitudes/', views.mis_solicitudes_agricultor, name='mis_solicitudes'),
    path('crear/', views.crear_solicitud, name='crear_solicitud'),
    path('cancelar/<int:solicitud_id>/', views.cancelar_solicitud, name='cancelar_solicitud'),
    path('historial/', views.historial_analisis_agricultor, name='historial'),
    path('comparar/', views.comparar_analisis_agricultor, name='comparar_analisis'),
    path('resultado/<int:solicitud_id>/', views.resultado_detalle_agricultor, name='resultado_detalle'),
    path('historial/exportar-pdf/', views.exportar_historial_pdf, name='exportar_historial_pdf'),
    path('historial/exportar-excel/', views.exportar_historial_excel, name='exportar_historial_excel'),
    path('resultado/<int:solicitud_id>/exportar-pdf/', views.exportar_analisis_individual_pdf, name='exportar_analisis_pdf'),
    path('resultado/<int:solicitud_id>/exportar-excel/', views.exportar_analisis_individual_excel, name='exportar_analisis_excel'),
]
