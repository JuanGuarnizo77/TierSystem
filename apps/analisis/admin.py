from django.contrib import admin
from .models import RegistroAnalisis, PuntoMuestreo, RecomendacionAnalisis

@admin.register(RegistroAnalisis)
class RegistroAnalisisAdmin(admin.ModelAdmin):
    list_display = ('id', 'solicitud', 'ph', 'nitrogeno', 'fosforo', 'potasio', 'fecha_analisis')
    search_fields = ('solicitud__terreno__nombre', 'solicitud__agricultor__username')

@admin.register(PuntoMuestreo)
class PuntoMuestreoAdmin(admin.ModelAdmin):
    list_display = ('id', 'solicitud', 'numero', 'estado', 'latitud', 'longitud', 'altitud', 'ph', 'fecha_toma')
    list_filter = ('estado', 'solicitud')
    search_fields = ('solicitud__terreno__nombre',)

@admin.register(RecomendacionAnalisis)
class RecomendacionAnalisisAdmin(admin.ModelAdmin):
    list_display = ('id', 'analisis', 'nombre_cultivo', 'porcentaje_compatibilidad', 'viabilidad')
    list_filter = ('viabilidad',)
    search_fields = ('nombre_cultivo', 'analisis__solicitud__terreno__nombre')

