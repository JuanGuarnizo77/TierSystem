from django.urls import path
from . import views

urlpatterns = [
    path('cultivos/', views.api_obtener_cultivos, name='api_obtener_cultivos'),
    path('diagnosticar/', views.api_diagnosticar_ia, name='api_diagnosticar_ia'),
]
