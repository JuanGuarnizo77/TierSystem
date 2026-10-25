"""
Modelo de Dominio: Resultados de Análisis Edafológicos y Muestreo Espacial.
============================================================================
Define las entidades estructurales del flujo de laboratorio de suelos en TierSystem:
  1. `RegistroAnalisis`: Informe consolidado final de una solicitud, que almacena
     los promedios aritméticos de los parámetros fisicoquímicos y el dictamen agronómico.
  2. `PuntoMuestreo`: Estación discreta de muestreo en campo con georreferenciación 3D
     (latitud, longitud y altitud msnm) y lecturas individuales estabilizadas.
  3. `RecomendacionAnalisis`: Veredicto agronómico multivariado que vincula el análisis
     con cultivos alternativos y planes de fertilización/enmienda de suelos.
"""

from django.db import models
from apps.solicitudes.models import SolicitudAnalisis


class RegistroAnalisis(models.Model):
    """
    Consolidado oficial de resultados fisicoquímicos para una solicitud de análisis.

    Se genera atómicamente una vez el laboratorista finaliza la toma de todos
    los puntos de muestreo requeridos según la densidad del lote.
    """
    solicitud = models.OneToOneField(
        SolicitudAnalisis,
        on_delete=models.CASCADE,
        related_name='analisis_resultado',
        help_text="Solicitud agronómica a la que pertenece este resultado analítico"
    )

    # Parámetros fisicoquímicos promedio consolidados de la parcela
    humedad = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Humedad volumétrica promedio del suelo (%)"
    )
    temperatura = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Temperatura promedio del suelo (°C)"
    )
    conductividad = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Conductividad eléctrica media (salinidad en µS/cm o dS/m)"
    )
    ph = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text="Potencial de hidrógeno medio (escala 0-14)"
    )
    nitrogeno = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Nitrógeno disponible medio (mg/kg)"
    )
    fosforo = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Fósforo asimilable medio (mg/kg)"
    )
    potasio = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Potasio intercambiable medio (mg/kg)"
    )

    # Dictamen emitido por el motor de inferencia (IA / Gemini o Heurístico Local)
    diagnostico_ia = models.TextField(
        blank=True,
        null=True,
        help_text="Cuerpo JSON serializado con el reporte agronómico y recomendaciones"
    )

    fecha_analisis = models.DateTimeField(
        auto_now_add=True,
        help_text="Marca temporal de generación y cierre del análisis"
    )

    def __str__(self):
        """Identificador textual para auditoría del análisis."""
        return f"Análisis de Solicitud #{self.solicitud.id} - {self.fecha_analisis.strftime('%d/%m/%Y')}"


class PuntoMuestreo(models.Model):
    """
    Estación o sub-muestra individual capturada en campo por el laboratorista.

    Forma parte de la grilla de muestreo en zig-zag diseñada para representar
    la heterogeneidad espacial del suelo dentro del predio agrícola.
    """
    solicitud = models.ForeignKey(
        SolicitudAnalisis,
        on_delete=models.CASCADE,
        related_name='puntos_muestreo',
        help_text="Solicitud a la que pertenece esta estación de muestreo"
    )
    numero = models.IntegerField(
        help_text="Número secuencial del punto en la ruta de muestreo (1, 2, ... N)"
    )
    estado = models.CharField(
        max_length=20,
        default='PENDIENTE',
        choices=[('PENDIENTE', 'Pendiente'), ('TOMADO', 'Tomado')],
        help_text="Estado de recolección en campo de la estación"
    )

    # Georreferenciación GNSS 3D del punto físico
    latitud = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="Latitud WGS84 capturada por el GPS del dispositivo móvil"
    )
    longitud = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="Longitud WGS84 capturada por el GPS del dispositivo móvil"
    )
    altitud = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Altitud ortométrica en metros sobre el nivel del mar (msnm)"
    )
    fecha_toma = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora exacta en la que se fijaron los datos del sensor"
    )

    # Mediciones fisicoquímicas puntuales registradas por la sonda IoT
    humedad = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperatura = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    conductividad = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    nitrogeno = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fosforo = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    potasio = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['solicitud', 'numero']
        verbose_name = 'Punto de Muestreo'
        verbose_name_plural = 'Puntos de Muestreo'

    def __str__(self):
        """Etiqueta descriptiva con altitud si se encuentra georreferenciada."""
        alt_str = f" ({self.altitud} msnm)" if self.altitud else ""
        return f"Punto {self.numero} - Solicitud #{self.solicitud.id}{alt_str}"


class RecomendacionAnalisis(models.Model):
    """
    Recomendación agronómica específica asociada a un análisis de suelo finalizado.

    Almacena los cultivos evaluados como aptos para el terreno según su fertilidad
    actual, su porcentaje de afinidad biológica y sugerencias nutricionales.
    """
    analisis = models.ForeignKey(
        RegistroAnalisis,
        on_delete=models.CASCADE,
        related_name='recomendaciones',
        help_text="Registro de análisis matriz del cual se desprende la recomendación"
    )
    cultivo = models.ForeignKey(
        'cultivos.Cultivo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recomendaciones_analisis',
        help_text="Referencia relacional a la especie en el catálogo de cultivos"
    )
    nombre_cultivo = models.CharField(
        max_length=120,
        help_text="Nombre común del cultivo evaluado"
    )
    porcentaje_compatibilidad = models.FloatField(
        default=0.0,
        help_text="Puntuación cuantitativa de afinidad edáfica (0.0% a 100.0%)"
    )
    viabilidad = models.CharField(
        max_length=50,
        default='Alta',
        help_text="Clasificación cualitativa de aptitud agronómica (Alta, Media, Baja)"
    )
    descripcion = models.TextField(
        blank=True,
        default='',
        help_text="Justificación técnica de la compatibilidad y alertas nutricionales"
    )
    plan_fertilizacion = models.TextField(
        blank=True,
        default='',
        help_text="Plan propuesto de enmiendas, correctivos de acidez y dosis de macronutrientes"
    )

    class Meta:
        ordering = ['-porcentaje_compatibilidad']
        verbose_name = 'Recomendación de Análisis'
        verbose_name_plural = 'Recomendaciones de Análisis'

    def __str__(self):
        """Resumen textual del cultivo sugerido y su compatibilidad."""
        return f"{self.nombre_cultivo} ({self.porcentaje_compatibilidad}%) - Solicitud #{self.analisis.solicitud_id}"
