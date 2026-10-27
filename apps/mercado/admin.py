"""
Configuración del Panel Administrativo de Django para Compradores.
==================================================================
Registra el modelo `Comprador` en la interfaz de administración, facilitando
la vinculación horizontal de cultivos (`filter_horizontal`) y filtros de búsqueda.
"""

from django.contrib import admin
from .models import Comprador


@admin.register(Comprador)
class CompradorAdmin(admin.ModelAdmin):
    """Panel de administración del directorio comercial de compradores del Huila."""
    list_display = (
        'nombre',
        'tipo',
        'municipio',
        'contacto',
        'precio_referencia',
        'activo',
    )
    list_filter = ('activo', 'tipo', 'municipio')
    search_fields = ('nombre', 'municipio', 'contacto')
    # Selector de doble lista interactivo para relacionar múltiples cultivos
    filter_horizontal = ('cultivos_rel',)
