from django.urls import path
from . import views

app_name = 'solicitudes'

urlpatterns = [
    path('pendientes/', views.solicitudes_pendientes, name='pendientes'),
    path('mis-tareas/', views.solicitudes_asignadas, name='mis_tareas'),
    path('aceptar/<int:solicitud_id>/', views.aceptar_solicitud, name='aceptar'),
    path('rechazar/<int:solicitud_id>/', views.rechazar_solicitud, name='rechazar'),
]
