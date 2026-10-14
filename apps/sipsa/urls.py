from django.urls import path
from . import views

app_name = 'sipsa'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cultivo/<int:cultivo_id>/', views.detalle_cultivo, name='detalle_cultivo'),
    path('cultivo/<int:cultivo_id>/api/', views.api_json, name='api_json'),
    path('actualizar/', views.actualizar_precios_view, name='actualizar_precios'),
]
