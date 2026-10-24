from django.contrib import admin
from .models import ConfiguracionGlobal


@admin.register(ConfiguracionGlobal)
class ConfiguracionGlobalAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tiempo_espera_ia', 'accion_fallo_ia')
