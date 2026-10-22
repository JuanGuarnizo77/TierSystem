from django.contrib import admin
from .models import CultivoIdeal, ConfiguracionGlobal

@admin.register(CultivoIdeal)
class CultivoIdealAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'clima', 'altitud_min', 'altitud_max', 'ph_min', 'ph_max', 'activo')
    list_filter = ('categoria', 'clima', 'activo')
    search_fields = ('nombre', 'categoria', 'descripcion')

@admin.register(ConfiguracionGlobal)
class ConfiguracionGlobalAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tiempo_espera_ia', 'accion_fallo_ia')

