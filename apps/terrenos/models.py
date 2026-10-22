from django.db import models
from django.contrib.auth.models import User

class Terreno(models.Model):
    agricultor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='terrenos')
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, help_text="Vereda, municipio, etc.")
    hectareas = models.DecimalField(max_digits=8, decimal_places=2)
    cultivo_principal = models.CharField(max_length=100, blank=True, null=True)
    cultivo_ref = models.ForeignKey(
        'ia_recomendaciones.CultivoIdeal',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='terrenos',
        help_text="Enlace relacional al cultivo en catálogo maestro"
    )
    altitud_promedio = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="Altitud promedio en msnm")
    coordenadas_poligono = models.TextField(blank=True, null=True, help_text="Coordenadas JSON del polígono")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Terreno'
        verbose_name_plural = 'Terrenos'

    def __str__(self):
        return f"{self.nombre} ({self.agricultor.username})"
