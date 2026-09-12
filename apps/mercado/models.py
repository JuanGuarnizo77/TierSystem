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
