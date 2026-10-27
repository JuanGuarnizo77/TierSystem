"""
Enrutamiento URL de Gestión de Solicitudes para el Rol Laboratorista.
====================================================================
Define las rutas web accesibles por el personal técnico de laboratorio:
  - `pendientes/`: Bandeja de entrada de solicitudes sin asignar.
  - `mis-tareas/`: Tareas aceptadas asignadas al técnico autenticado.
  - `aceptar/<id>/`: Transición atómica de estado a 'ASIGNADA' con fecha de visita.
  - `rechazar/<id>/`: Transición de estado a 'RECHAZADA' con notificación por correo.
"""

from django.urls import path
from . import views

# Espacio de nombres para laboratoristas (solicitudes:pendientes, etc.)
app_name = 'solicitudes'

urlpatterns = [
    # Bandeja general de solicitudes entrantes pendientes de atención
    path('pendientes/', views.solicitudes_pendientes, name='pendientes'),

    # Listado de solicitudes activas asignadas al laboratorista autenticado
    path('mis-tareas/', views.solicitudes_asignadas, name='mis_tareas'),

    # Operación de aceptación y asignación técnica con programación de visita
    path('aceptar/<int:solicitud_id>/', views.aceptar_solicitud, name='aceptar'),

    # Operación de descarte o rechazo de solicitud
    path('rechazar/<int:solicitud_id>/', views.rechazar_solicitud, name='rechazar'),
]
