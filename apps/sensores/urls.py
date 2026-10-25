"""
Enrutamiento URL para la Ingesta de Sensores IoT y Telemetría.
=============================================================
Define los puntos de entrada para la recepción de tramas HTTP desde microcontroladores
ESP32, la estabilización estadística de señales y el guardado de puntos de muestreo.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Ingesta periódica directa de tramas de telemetría IoT desde el ESP32
    path('lecturas/', views.recibir_datos_sensor, name='api_recibir_datos'),

    # Consulta de lecturas estabilizadas mediante cálculo de moda en ventana móvil de 15s
    path('captura-estable/', views.captura_estable, name='api_captura_estable'),

    # Persistencia de lecturas consolidadas y coordenadas 3D en la estación de muestreo
    path('punto/<int:punto_id>/guardar/', views.guardar_punto, name='api_guardar_punto'),
]
