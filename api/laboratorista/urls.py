from django.urls import path

from .views_dashboard import dashboard_view
from .views_solicitudes import (
    pendientes_view,
    mis_tareas_view,
    aceptar_view,
    rechazar_view,
)

urlpatterns = [
    path('dashboard/', dashboard_view, name='laboratorista_dashboard'),
    path('solicitudes/pendientes/', pendientes_view, name='laboratorista_pendientes'),
    path('solicitudes/mis-tareas/', mis_tareas_view, name='laboratorista_mis_tareas'),
    path('solicitudes/<int:solicitud_id>/aceptar/', aceptar_view, name='laboratorista_aceptar'),
    path('solicitudes/<int:solicitud_id>/rechazar/', rechazar_view, name='laboratorista_rechazar'),
]