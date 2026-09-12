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
    )

    agricultor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_creadas')
    terreno = models.ForeignKey(Terreno, on_delete=models.CASCADE, related_name='solicitudes')
    laboratorista_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_asignadas')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_visita = models.DateField(null=True, blank=True)
    notas_agricultor = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Solicitud #{self.id} - {self.terreno.nombre} ({self.get_estado_display()})"
