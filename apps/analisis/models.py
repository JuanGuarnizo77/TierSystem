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
