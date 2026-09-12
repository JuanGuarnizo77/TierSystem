from django.urls import path
from . import views

app_name = 'solicitudes_agricultor'

urlpatterns = [
    path('mis-solicitudes/', views.mis_solicitudes_agricultor, name='mis_solicitudes'),
    path('crear/', views.crear_solicitud, name='crear_solicitud'),
]
