"""
Configuración del Panel Administrativo de Django para Parámetros Globales.
==========================================================================
Expone la entidad singleton `ConfiguracionGlobal` en el panel de administración,
permitiendo regular los umbrales de sensores y el comportamiento de la IA.
"""

from django.contrib import admin
from .models import ConfiguracionGlobal


@admin.register(ConfiguracionGlobal)
class ConfiguracionGlobalAdmin(admin.ModelAdmin):
    """Panel administrativo para la calibración global y gobernanza de la IA."""
    list_display = ('__str__', 'tiempo_espera_ia', 'accion_fallo_ia')
