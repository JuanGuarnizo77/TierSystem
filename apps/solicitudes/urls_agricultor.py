from django.urls import path
from . import views

app_name = 'solicitudes_agricultor'

urlpatterns = [
    path('mis-solicitudes/', views.mis_solicitudes_agricultor, name='mis_solicitudes'),
    path('crear/', views.crear_solicitud, name='crear_solicitud'),
    path('cancelar/<int:solicitud_id>/', views.cancelar_solicitud, name='cancelar_solicitud'),
    path('historial/', views.historial_analisis_agricultor, name='historial'),
]
