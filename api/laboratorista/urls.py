"""
Enrutador de Endpoints para el Perfil Laboratorista / Técnico de Campo.
Expone las operaciones requeridas por la aplicación móvil para:
1. Gestión de órdenes de servicio (banco global, asignación, rechazo y tareas activas).
2. Protocolo de muestreo en campo (lectura de sensor ESP32, persistencia de puntos 3D).
3. Consolidación de análisis edafológico (cálculo de medias y diagnóstico dual).
4. Historial técnico y consultas agronómicas personalizadas para el productor.
"""

from django.urls import path

from .views_dashboard import dashboard_view
from .views_solicitudes import (
    pendientes_view,
    mis_tareas_view,
    aceptar_view,
    rechazar_view,
    banco_view,
)
from .views_consulta import consulta_cultivo_view
from .views_historial import historial_view, resultado_view
from .views_muestreo import (
    muestreo_view,
    sensor_view,
    guardar_punto_view,
    generar_analisis_view,
)

urlpatterns = [
    # Métricas y contadores de solicitudes activas y análisis completados
    path('dashboard/', dashboard_view, name='laboratorista_dashboard'),

    # Banco general de solicitudes de agricultores en estado PENDIENTE
    path('solicitudes/pendientes/', pendientes_view, name='laboratorista_pendientes'),
    path('solicitudes/banco/', banco_view, name='laboratorista_banco'),

    # Órdenes de servicio asignadas al laboratorista autenticado
    path('solicitudes/mis-tareas/', mis_tareas_view, name='laboratorista_mis_tareas'),

    # Transición de estado: Aceptación de visita con asignación de fecha y envío de email
    path('solicitudes/<int:solicitud_id>/aceptar/', aceptar_view, name='laboratorista_aceptar'),

    # Rechazo o devolución de solicitud al banco de pendientes
    path('solicitudes/<int:solicitud_id>/rechazar/', rechazar_view, name='laboratorista_rechazar'),

    # Historial de estudios de suelo completados por el técnico
    path('historial/', historial_view, name='laboratorista_historial'),

    # Consulta del reporte agronómico y plan de fertilización de una orden
    path('resultados/<int:solicitud_id>/', resultado_view, name='laboratorista_resultado'),

    # Telemetría en tiempo real: lee el valor estabilizado del microcontrolador ESP32
    path('muestreo/sensor/', sensor_view, name='laboratorista_sensor'),

    # Consulta y generación de la cuadrícula de puntos según hectáreas del predio
    path('muestreo/<int:solicitud_id>/', muestreo_view, name='laboratorista_muestreo'),

    # Guarda una perforación física individual georreferenciada (lat, lon, alt, NPK, pH)
    path('muestreo/puntos/<int:punto_id>/guardar/', guardar_punto_view, name='laboratorista_guardar_punto'),

    # Promedia los puntos recolectados, invoca motor agronómico y completa la solicitud
    path('muestreo/<int:solicitud_id>/generar/', generar_analisis_view, name='laboratorista_generar_analisis'),

    # Consulta agronómica interactiva de compatibilidad para un cultivo específico
    path('resultados/<int:solicitud_id>/consulta-cultivo/', consulta_cultivo_view, name='laboratorista_consulta_cultivo'),
]