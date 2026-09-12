from django.urls import path
from . import views

app_name = 'analisis'

urlpatterns = [
    path('historial/', views.historial_analisis, name='historial'),
]
