"""
Configuración del Panel Administrativo de Django para Terrenos.
==============================================================
Registra la entidad `Terreno` en el panel de administración central, permitiendo
a los administradores inspeccionar predios, áreas en hectáreas y georreferenciación.
"""

from django.contrib import admin
from .models import Terreno


@admin.register(Terreno)
class TerrenoAdmin(admin.ModelAdmin):
    """Administración y auditoría de fincas agrícolas registradas en el sistema."""
    list_display = ('nombre', 'agricultor', 'ubicacion', 'hectareas', 'cultivo_ref', 'fecha_registro')
    list_filter = ('cultivo_ref', 'fecha_registro')
    search_fields = ('nombre', 'ubicacion', 'agricultor__username', 'agricultor__email')
    ordering = ('-fecha_registro',)
