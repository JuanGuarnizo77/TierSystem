from django.db import models


class Comprador(models.Model):
    """Compradores mayoristas, cooperativas y plazas de mercado del Huila."""
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=50, help_text="Cooperativa, Plaza de Mercado, Intermediario, Exportador")
    municipio = models.CharField(max_length=100, default='Neiva, Huila')
    contacto = models.CharField(max_length=100, blank=True, default='')
    cultivos_rel = models.ManyToManyField(
        'cultivos.Cultivo',
        blank=True,
        related_name='compradores_interesados',
        help_text="Cultivos de interés vinculados relacionalmente"
    )
    precio_referencia = models.CharField(max_length=100, null=True, blank=True)
    activo = models.BooleanField(default=True)
    email = models.EmailField(blank=True, default='')
    whatsapp = models.CharField(max_length=20, blank=True, default='')
    sitio_web = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        verbose_name = 'Comprador'
        verbose_name_plural = 'Compradores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def cultivos_interes(self):
        """Compatibilidad hacia atrás con vistas y plantillas."""
        nombres = [c.nombre for c in self.cultivos_rel.all()]
        return ", ".join(nombres) if nombres else "Varios cultivos"
