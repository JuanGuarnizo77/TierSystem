from django.contrib import admin
from .models import CultivoIdeal

@admin.register(CultivoIdeal)
class CultivoIdealAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'humedad_min', 'temperatura_min', 'ph_min', 'nitrogeno_min')
    search_fields = ('nombre',)
