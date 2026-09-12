from django.db import models
from django.contrib.auth.models import User

class Terreno(models.Model):
    agricultor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='terrenos')
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, help_text="Vereda, municipio, etc.")
    hectareas = models.DecimalField(max_digits=8, decimal_places=2)
    cultivo_principal = models.CharField(max_length=100, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.agricultor.username})"
