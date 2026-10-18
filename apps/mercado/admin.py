from django.contrib import admin
from .models import ProductoMercado, PrecioMercado, Comprador


@admin.register(ProductoMercado)
class ProductoMercadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'vendedor', 'precio', 'cantidad_disponible', 'unidad_medida', 'activo', 'fecha_publicacion')
    list_filter = ('activo', 'unidad_medida', 'fecha_publicacion')
    search_fields = ('nombre', 'vendedor__username', 'descripcion')


@admin.register(PrecioMercado)
class PrecioMercadoAdmin(admin.ModelAdmin):
    list_display = ('cultivo_nombre', 'region', 'precio_promedio', 'precio_local', 'unidad', 'tendencia', 'variacion_porcentaje', 'fuente', 'ultima_actualizacion')
    list_filter = ('tendencia', 'ultima_actualizacion', 'region', 'cultivo_nombre')
    search_fields = ('cultivo_nombre', 'fuente', 'region')


@admin.register(Comprador)
class CompradorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'municipio', 'contacto', 'cultivos_interes', 'precio_referencia', 'activo')
    list_filter = ('activo', 'tipo', 'municipio')
    search_fields = ('nombre', 'municipio', 'cultivos_interes', 'contacto')
