"""
Configuración del Panel Administrativo de Django para Cultivos.
==============================================================
Registra el modelo `Cultivo` en el administrador de Django, configurando
filtros de búsqueda, visualización de rangos agroclimáticos clave y control
de activación/desactivación de especies agrícolas en el Huila.
"""

from django.contrib import admin
from .models import Cultivo


@admin.register(Cultivo)
class CultivoAdmin(admin.ModelAdmin):
    """
    Administración centralizada del catálogo de especies agrícolas.

    Permite a los agrónomos administradores afinar los rangos de calibración
    edafológica (pH, altitud) y habilitar o inhabilitar cultivos según temporadas.
    """
    # Columnas principales en la vista de lista tabular
    list_display = (
        'nombre',
        'categoria',
        'clima',
        'altitud_min',
        'altitud_max',
        'ph_min',
        'ph_max',
        'activo',
    )

    # Filtros laterales por taxonomía, clima y estado de activación
    list_filter = ('categoria', 'clima', 'activo')

    # Búsqueda textual sobre nombres, taxonomía botánica y descripciones agronómicas
    search_fields = ('nombre', 'nombre_cientifico', 'categoria', 'descripcion')

    # Ordenamiento alfabético por defecto
    ordering = ('nombre',)
