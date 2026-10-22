from django.db import models
from apps.solicitudes.models import SolicitudAnalisis

class RegistroAnalisis(models.Model):
    solicitud = models.OneToOneField(SolicitudAnalisis, on_delete=models.CASCADE, related_name='analisis_resultado')
    
    # Parámetros capturados
    humedad = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    temperatura = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    conductividad = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    ph = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    nitrogeno = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    fosforo = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    potasio = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Resultado IA (JSON en string)
    diagnostico_ia = models.TextField(blank=True, null=True, help_text="JSON string con el reporte generado")
    
    fecha_analisis = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Análisis de Solicitud #{self.solicitud.id} - {self.fecha_analisis.strftime('%d/%m/%Y')}"

class PuntoMuestreo(models.Model):
    solicitud = models.ForeignKey(SolicitudAnalisis, on_delete=models.CASCADE, related_name='puntos_muestreo')
    numero = models.IntegerField(help_text="Número secuencial del punto de muestreo")
    estado = models.CharField(max_length=20, default='PENDIENTE', choices=[('PENDIENTE', 'Pendiente'), ('TOMADO', 'Tomado')])
    
    # Georreferenciación 3D del punto en campo
    latitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, help_text="Latitud GPS")
    longitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, help_text="Longitud GPS")
    altitud = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="Altitud en msnm")
    fecha_toma = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora de captura de la muestra")

    # Parámetros fisicoquímicos
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
        alt_str = f" ({self.altitud} msnm)" if self.altitud else ""
        return f"Punto {self.numero} - Solicitud #{self.solicitud.id}{alt_str}"


class RecomendacionAnalisis(models.Model):
    analisis = models.ForeignKey(RegistroAnalisis, on_delete=models.CASCADE, related_name='recomendaciones')
    cultivo = models.ForeignKey('ia_recomendaciones.CultivoIdeal', on_delete=models.SET_NULL, null=True, blank=True, related_name='recomendaciones_analisis')
    nombre_cultivo = models.CharField(max_length=120)
    porcentaje_compatibilidad = models.FloatField(default=0.0)
    viabilidad = models.CharField(max_length=50, default='Alta', help_text="Alta, Media, Baja")
    descripcion = models.TextField(blank=True, default='')
    plan_fertilizacion = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-porcentaje_compatibilidad']
        verbose_name = 'Recomendación de Análisis'
        verbose_name_plural = 'Recomendaciones de Análisis'

    def __str__(self):
        return f"{self.nombre_cultivo} ({self.porcentaje_compatibilidad}%) - Solicitud #{self.analisis.solicitud_id}"
