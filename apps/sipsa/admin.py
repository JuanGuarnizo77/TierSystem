from django.contrib import admin
from .models import PrecioSemanal


@admin.register(PrecioSemanal)
class PrecioSemanalAdmin(admin.ModelAdmin):
    list_display = (
        'cultivo', 'fecha_semana', 'semana_label',
        'precio_kg', 'precio_local', 'fuente', 'fecha_registro')
    list_filter = ('cultivo', 'fecha_semana')
    search_fields = ('cultivo__nombre', 'semana_label', 'fuente')
    date_hierarchy = 'fecha_semana'
