from django.db import models
from django.contrib.auth.models import User
from apps.terrenos.models import Terreno

class SolicitudAnalisis(models.Model):
    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('ASIGNADA', 'Asignada'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADA', 'Completada'),
        ('RECHAZADA', 'Rechazada'),
        ('CANCELADA', 'Cancelada'),
    )
    MODALIDADES = (
        ('VISITA', 'Solicitar Visita en Campo'),
        ('LLEVAR_MUESTRA', 'Llevar Muestra al Laboratorio'),
    )

    agricultor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_creadas')
    terreno = models.ForeignKey(Terreno, on_delete=models.CASCADE, related_name='solicitudes')
    laboratorista_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_asignadas')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    # Campos de cultivo y modalidad
    cultivo_deseado = models.CharField(max_length=100, default='No especificado')
    cultivo_deseado_ref = models.ForeignKey(
        'ia_recomendaciones.CultivoIdeal',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='solicitudes_asociadas',
        help_text="Enlace relacional al cultivo deseado en catálogo"
    )
    modalidad = models.CharField(max_length=20, choices=MODALIDADES, default='VISITA')
    
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_visita = models.DateField(null=True, blank=True)
    notas_agricultor = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Solicitud de Análisis'
        verbose_name_plural = 'Solicitudes de Análisis'

    def __str__(self):
        return f"Solicitud #{self.id} - {self.terreno.nombre} ({self.get_estado_display()})"
