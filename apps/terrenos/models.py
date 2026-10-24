from django.db import models
from django.contrib.auth.models import User

class Terreno(models.Model):
    agricultor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='terrenos')
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, help_text="Vereda, municipio, etc.")
    hectareas = models.DecimalField(max_digits=8, decimal_places=2)
    cultivo_ref = models.ForeignKey(
        'cultivos.Cultivo',
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

    @property
    def cultivo_principal(self):
        """Compatibilidad hacia atrás con vistas y plantillas."""
        return self.cultivo_ref.nombre if self.cultivo_ref else 'No especificado'

    @cultivo_principal.setter
    def cultivo_principal(self, value):
        if not value:
            self.cultivo_ref = None
            return
        from apps.cultivos.models import Cultivo
        if isinstance(value, Cultivo):
            self.cultivo_ref = value
        elif str(value).isdigit():
            self.cultivo_ref = Cultivo.objects.filter(id=int(value)).first()
        else:
            self.cultivo_ref = Cultivo.objects.filter(nombre__icontains=str(value).strip()).first()

    def __str__(self):
        return f"{self.nombre} ({self.agricultor.username})"
