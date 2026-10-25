"""
Enrutamiento URL para la Gestión de Fincas y Terrenos.
=====================================================
Define los patrones de ruta para la administración web y operaciones AJAX
de predios agrícolas asociados a los productores.
"""

from django.urls import path
from . import views

# Espacio de nombres de la aplicación para resolución reversa (terrenos:mis_terrenos, etc.)
app_name = 'terrenos'

urlpatterns = [
    # Vista principal de visualización de parcelas registradas
    path('', views.mis_terrenos, name='mis_terrenos'),

    # Operaciones asíncronas de mutación (CRUD AJAX)
    path('crear/', views.crear_terreno, name='crear_terreno'),
    path('eliminar/<int:terreno_id>/', views.eliminar_terreno, name='eliminar_terreno'),
    path('editar/<int:terreno_id>/', views.editar_terreno, name='editar_terreno'),
]
