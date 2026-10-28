"""
Enrutamiento URL para el Motor de IA y Recomendaciones Agronómicas.
===================================================================
Expone los endpoints de la API REST para la inferencia con modelos generativos (Gemini),
el motor edafológico determinista offline, la agregación estadística de muestras de campo
y la sincronización de diagnósticos almacenados localmente en Dexie.js (IndexedDB).
"""

from django.urls import path
from . import views

urlpatterns = [
    # Descarga del catálogo agronómico para almacenamiento en cliente PWA
    path('cultivos/', views.api_obtener_cultivos, name='api_obtener_cultivos'),

    # Inferencia híbrida (Gemini Flash con fallback offline al motor heurístico)
    path('diagnosticar/', views.api_diagnosticar_ia, name='api_diagnosticar_ia'),

    # Cálculo y agregación de promedios de estaciones de muestreo
    path('promedio_puntos/', views.api_promedio_puntos, name='api_promedio_puntos'),

    # Compartir resultados consolidados con el agricultor y cerrar solicitud
    path('compartir/', views.api_compartir_resultado, name='api_compartir_resultado'),

    # Sincronización por lotes de lecturas y análisis recopilados en modo offline
    path('sincronizar-offline/', views.api_sincronizar_offline, name='api_sincronizar_offline'),

    # Asistente agronómico conversacional para consultas específicas del productor
    path('consultar-agricultor/', views.api_consultar_ia_agricultor, name='api_consultar_ia_agricultor'),

    # Asesor edafológico y botánico abierto (con filtro estricto de dominio agrícola)
    path('asesor-suelo/', views.api_asesor_agronomico, name='api_asesor_agronomico'),
]
