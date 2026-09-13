from django.urls import path
from . import views

app_name = 'terrenos'

urlpatterns = [
    path('', views.mis_terrenos, name='mis_terrenos'),
    path('crear/', views.crear_terreno, name='crear_terreno'),
    path('eliminar/<int:terreno_id>/', views.eliminar_terreno, name='eliminar_terreno'),
    path('editar/<int:terreno_id>/', views.editar_terreno, name='editar_terreno'),
]
