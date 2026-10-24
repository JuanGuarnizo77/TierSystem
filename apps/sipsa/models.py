from django.db import models


class PrecioSemanal(models.Model):
    """Precio mayorista oficial DANE para un cultivo en una semana dada."""

    cultivo = models.ForeignKey(
        'cultivos.Cultivo', on_delete=models.CASCADE,
        related_name='precios_semanales')
    fecha_semana = models.DateField(
        help_text="Fecha de inicio de la semana SIPSA (lunes)")
    semana_label = models.CharField(
        max_length=30,
        help_text="Etiqueta legible, ej. 'Sem 42-2026'")
    precio_kg = models.DecimalField(max_digits=12, decimal_places=2)
    precio_local = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text="Precio regional Huila (~97% del promedio nacional)")
    mercado_referencia = models.CharField(
        max_length=200, default='SIPSA — Plazas Mayoristas Colombia')
    fuente = models.CharField(max_length=300, default='SIPSA / DANE')
    fuente_url = models.CharField(max_length=500, blank=True, default='')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cultivo', 'fecha_semana')
        ordering = ['cultivo', '-fecha_semana']
        verbose_name = 'Precio Semanal SIPSA'
        verbose_name_plural = 'Precios Semanales SIPSA'

    def __str__(self):
        return f"{self.cultivo.nombre} — {self.semana_label} — ${self.precio_kg}"
