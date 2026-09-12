from django.urls import path
from . import views

app_name = 'mercado'

urlpatterns = [
    path('', views.mercado_publico, name='publico'),
    path('mi-tienda/', views.mi_tienda, name='mi_tienda'),
    path('agregar/', views.agregar_producto, name='agregar_producto'),
    path('eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
]
