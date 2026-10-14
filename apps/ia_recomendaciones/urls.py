from django.urls import path
from . import views

urlpatterns = [
    path('cultivos/', views.api_obtener_cultivos, name='api_obtener_cultivos'),
    path('diagnosticar/', views.api_diagnosticar_ia, name='api_diagnosticar_ia'),
    path('promedio_puntos/', views.api_promedio_puntos, name='api_promedio_puntos'),
    path('compartir/', views.api_compartir_resultado, name='api_compartir_resultado'),
    path('sincronizar-offline/', views.api_sincronizar_offline, name='api_sincronizar_offline'),
    path('consultar-agricultor/', views.api_consultar_ia_agricultor, name='api_consultar_ia_agricultor'),
]
