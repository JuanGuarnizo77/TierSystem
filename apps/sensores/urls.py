from django.urls import path
from . import views

urlpatterns = [
    path('lecturas/', views.recibir_datos_sensor, name='api_recibir_datos'),
    path('captura-estable/', views.captura_estable, name='api_captura_estable'),
]
