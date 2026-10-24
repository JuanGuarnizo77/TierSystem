from django.contrib import admin
from .models import Comprador


@admin.register(Comprador)
class CompradorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'municipio', 'contacto', 'precio_referencia', 'activo')
    list_filter = ('activo', 'tipo', 'municipio')
    search_fields = ('nombre', 'municipio', 'contacto')
    filter_horizontal = ('cultivos_rel',)
