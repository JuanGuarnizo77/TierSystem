from django.contrib import admin
from .models import CultivoSipsa, PrecioSemanal, PrediccionPrecio


@admin.register(CultivoSipsa)
class CultivoSipsaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nombre_dane', 'unidad', 'categoria', 'activo')
    list_filter = ('activo', 'categoria')
    search_fields = ('nombre', 'nombre_dane', 'categoria')


@admin.register(PrecioSemanal)
class PrecioSemanalAdmin(admin.ModelAdmin):
    list_display = (
        'cultivo', 'fecha_semana', 'semana_label',
        'precio_kg', 'precio_local', 'fuente', 'fecha_registro')
    list_filter = ('cultivo', 'fecha_semana')
    search_fields = ('cultivo__nombre', 'semana_label', 'fuente')
    date_hierarchy = 'fecha_semana'


@admin.register(PrediccionPrecio)
class PrediccionPrecioAdmin(admin.ModelAdmin):
    list_display = (
        'cultivo', 'tendencia_predicha', 'confianza_pct',
        'precio_estimado', 'variacion_estimada_pct', 'semanas_usadas', 'fecha_calculo')
    list_filter = ('tendencia_predicha',)
    search_fields = ('cultivo__nombre',)
