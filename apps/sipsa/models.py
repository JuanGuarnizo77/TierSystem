"""
Modelo de Dominio: Series de Precios Agropecuarios Semanales (SIPSA/DANE).
=========================================================================
Modela el historial de cotizaciones oficiales reportadas por el Sistema de
Información de Precios y Abastecimiento del Sector Agropecuario (SIPSA) del DANE.

Permite contrastar los precios de plazas mayoristas nacionales con el mercado
regional del Huila (~97% del promedio nacional), alimentando el motor estadístico
de predicción de tendencias para brindar certidumbre económica al productor.
"""

from django.db import models


class PrecioSemanal(models.Model):
    """
    Registro semanal de cotización mayorista para un cultivo agrícola específico.

    Restricciones:
      - `unique_together = ('cultivo', 'fecha_semana')`: Asegura un único registro
        oficial por cultivo en cada semana epidemiológica/calendario.
    """
    cultivo = models.ForeignKey(
        'cultivos.Cultivo',
        on_delete=models.CASCADE,
        related_name='precios_semanales',
        help_text="Especie o variedad vegetal a la que corresponde la cotización"
    )
    fecha_semana = models.DateField(
        help_text="Fecha canónica de inicio de la semana SIPSA (día lunes)"
    )
    semana_label = models.CharField(
        max_length=30,
        help_text="Etiqueta legible en interfaz y reportes (ej. 'Sem 42-2026')"
    )
    precio_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Precio mayorista nacional por kilogramo en COP"
    )
    precio_local = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio de referencia en el mercado mayorista del Huila (~97% del promedio nacional)"
    )
    mercado_referencia = models.CharField(
        max_length=200,
        default='SIPSA — Plazas Mayoristas Colombia',
        help_text="Central de abastos o mercado de origen de la cotización"
    )
    fuente = models.CharField(
        max_length=300,
        default='SIPSA / DANE',
        help_text="Entidad oficial emisora de la estadística"
    )
    fuente_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Enlace directo a la API Socrata o boletín en datos.gov.co"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Marca temporal de sincronización en el sistema"
    )

    class Meta:
        unique_together = ('cultivo', 'fecha_semana')
        ordering = ['cultivo', '-fecha_semana']
        verbose_name = 'Precio Semanal SIPSA'
        verbose_name_plural = 'Precios Semanales SIPSA'

    def __str__(self):
        """Representación textual formal de la cotización."""
        return f"{self.cultivo.nombre} — {self.semana_label} — ${self.precio_kg}"
