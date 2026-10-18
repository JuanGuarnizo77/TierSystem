from django.db import models
from django.contrib.auth.models import User

class ProductoMercado(models.Model):
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='productos_venta')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_disponible = models.IntegerField(default=1)
    unidad_medida = models.CharField(max_length=50, default='kg', help_text="Ej. kg, bultos, toneladas")
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - {self.precio} COP"


class PrecioMercado(models.Model):
    TENDENCIA_CHOICES = [
        ('Alza', 'Alza'),
        ('Baja', 'Baja'),
        ('Estable', 'Estable'),
    ]

    cultivo_nombre = models.CharField(max_length=100)
    cultivo = models.ForeignKey(
        'sipsa.CultivoSipsa',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='precios_mercado',
        help_text="Enlace al catálogo canónico de cultivos",
    )
    region = models.CharField(max_length=100, default='Huila')
    precio_promedio = models.DecimalField(max_digits=12, decimal_places=2)
    precio_local = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unidad = models.CharField(max_length=30, default='kg')
    tendencia = models.CharField(max_length=20, choices=TENDENCIA_CHOICES, default='Estable')
    variacion_porcentaje = models.FloatField(default=0.0)
    fuente = models.CharField(max_length=200, default='SIPSA / DANE')
    # Campos añadidos FEAT-001
    semana_sipsa = models.CharField(max_length=100, blank=True, default='')
    fuente_url = models.CharField(max_length=500, blank=True, default='')
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.cultivo_nombre} - {self.region} - {self.precio_promedio}"

class Comprador(models.Model):
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=50, help_text="Cooperativa, Plaza de Mercado, Intermediario, Exportador")
    municipio = models.CharField(max_length=100, default='Neiva, Huila')
    contacto = models.CharField(max_length=100, blank=True, default='')
    cultivos_interes = models.TextField(help_text="Cultivos de interés separados por comas")
    precio_referencia = models.CharField(max_length=100, null=True, blank=True)
    activo = models.BooleanField(default=True)
    # Campos añadidos FEAT-001
    email = models.EmailField(blank=True, default='')
    whatsapp = models.CharField(max_length=20, blank=True, default='')
    sitio_web = models.CharField(max_length=200, blank=True, default='')

    def __str__(self):
        return self.nombre
