from django.db import models


class CultivoSipsa(models.Model):
    """Catálogo maestro de cultivos con precios SIPSA/DANE."""
    nombre = models.CharField(max_length=120, unique=True)
    nombre_dane = models.CharField(
        max_length=120, blank=True,
        help_text="Nombre exacto en dataset DANE para matching")
    unidad = models.CharField(max_length=50, default='kg')
    categoria = models.CharField(
        max_length=80, blank=True,
        help_text="Ej. Hortalizas, Frutas, Cereales, Tubérculos")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Cultivo SIPSA'
        verbose_name_plural = 'Cultivos SIPSA'

    def __str__(self):
        return self.nombre


class PrecioSemanal(models.Model):
    """Precio mayorista oficial DANE para un cultivo en una semana dada."""

    cultivo = models.ForeignKey(
        CultivoSipsa, on_delete=models.CASCADE,
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


class PrediccionPrecio(models.Model):
    """Predicción de tendencia calculada para la próxima semana."""
    PREDICCION_CHOICES = [
        ('Alza', 'Alza'),
        ('Baja', 'Baja'),
        ('Estable', 'Estable'),
    ]

    cultivo = models.OneToOneField(
        CultivoSipsa, on_delete=models.CASCADE,
        related_name='prediccion')
    tendencia_predicha = models.CharField(
        max_length=20, choices=PREDICCION_CHOICES)
    confianza_pct = models.FloatField(
        default=0.0,
        help_text="Porcentaje de confianza del modelo (0-100)")
    precio_estimado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Precio estimado para la próxima semana en COP/kg")
    variacion_estimada_pct = models.FloatField(
        default=0.0,
        help_text="Variación porcentual estimada respecto al último precio")
    semanas_usadas = models.IntegerField(
        default=0,
        help_text="Cantidad de semanas históricas usadas para calcular")
    fecha_calculo = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Predicción de Precio'
        verbose_name_plural = 'Predicciones de Precio'

    def __str__(self):
        return f"Pred. {self.cultivo.nombre}: {self.tendencia_predicha} ({self.confianza_pct:.0f}%)"
