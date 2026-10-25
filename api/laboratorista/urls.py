from django.urls import path

from .views_dashboard import dashboard_view
from .views_solicitudes import (
    pendientes_view,
    mis_tareas_view,
    aceptar_view,
    rechazar_view,
)
from .views_historial import historial_view, resultado_view
from .views_muestreo import muestreo_view, sensor_view, guardar_punto_view

urlpatterns = [
    path('dashboard/', dashboard_view, name='laboratorista_dashboard'),
    path('solicitudes/pendientes/', pendientes_view, name='laboratorista_pendientes'),
    path('solicitudes/mis-tareas/', mis_tareas_view, name='laboratorista_mis_tareas'),
    path('solicitudes/<int:solicitud_id>/aceptar/', aceptar_view, name='laboratorista_aceptar'),
    path('solicitudes/<int:solicitud_id>/rechazar/', rechazar_view, name='laboratorista_rechazar'),
    path('historial/', historial_view, name='laboratorista_historial'),
    path('resultados/<int:solicitud_id>/', resultado_view, name='laboratorista_resultado'),
    path('muestreo/sensor/', sensor_view, name='laboratorista_sensor'),
    path('muestreo/<int:solicitud_id>/', muestreo_view, name='laboratorista_muestreo'),
    path('muestreo/puntos/<int:punto_id>/guardar/', guardar_punto_view, name='laboratorista_guardar_punto'),
]