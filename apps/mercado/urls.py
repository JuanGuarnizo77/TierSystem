from django.urls import path
from . import views

app_name = 'mercado'

urlpatterns = [
    path('', views.precios_sipsa, name='precios_sipsa'),
    path('productos/', views.listado_productos, name='listado_productos'),
    path('api/cultivo/<str:cultivo_nombre>/', views.api_datos_cultivo_mercado, name='api_datos_cultivo'),
    path('mi-tienda/', views.mi_tienda, name='mi_tienda'),
    path('agregar-producto/', views.agregar_producto, name='agregar_producto'),
    path('eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('actualizar/', views.actualizar_precios_view, name='actualizar_precios'),
]
