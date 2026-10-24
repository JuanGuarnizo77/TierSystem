from django.contrib import admin
from .models import Cultivo

@admin.register(Cultivo)
class CultivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'clima', 'altitud_min', 'altitud_max', 'ph_min', 'ph_max', 'activo')
    list_filter = ('categoria', 'clima', 'activo')
    search_fields = ('nombre', 'nombre_cientifico', 'categoria', 'descripcion')
    ordering = ('nombre',)
