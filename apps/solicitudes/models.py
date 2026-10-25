"""
Modelo de Dominio: Ciclo de Vida de Solicitudes de Análisis Edafológico.
========================================================================
Define la entidad central `SolicitudAnalisis`, que gestiona la interacción
y el acuerdo de servicio entre el productor agrícola y el laboratorio de suelos.

Modela la máquina de estados de atención:
  PENDIENTE -> ASIGNADA -> EN_PROCESO -> COMPLETADA
  (con ramas terminales de RECHAZADA o CANCELADA).

Registra la modalidad de atención (visita técnica en finca o entrega directa
de muestra en el laboratorio del SENA La Angostura) y la trazabilidad de asignación.
"""

from django.db import models
from django.contrib.auth.models import User
from apps.terrenos.models import Terreno


class SolicitudAnalisis(models.Model):
    """
    Representa una petición formal de caracterización edáfica de un predio.

    Articula el flujo entre el agricultor solicitante, el predio objeto de estudio,
    el laboratorista asignado para la toma de muestras y el resultado de análisis final.
    """
    # Estados operativos del flujo de atención
    ESTADOS = (
        ('PENDIENTE', 'Pendiente'),
        ('ASIGNADA', 'Asignada'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADA', 'Completada'),
        ('RECHAZADA', 'Rechazada'),
        ('CANCELADA', 'Cancelada'),
    )

    # Modalidades operativas para la toma o recepción de muestras
    MODALIDADES = (
        ('VISITA', 'Solicitar Visita en Campo'),
        ('LLEVAR_MUESTRA', 'Llevar Muestra al Laboratorio'),
    )

    # Productor que origina el requerimiento
    agricultor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='solicitudes_creadas',
        help_text="Productor agrícola que crea la solicitud"
    )

    # Predio georreferenciado donde se efectuará el muestreo
    terreno = models.ForeignKey(
        Terreno,
        on_delete=models.CASCADE,
        related_name='solicitudes',
        help_text="Lote o finca agrícola a caracterizar"
    )

    # Técnico de laboratorio responsable del muestreo y dictamen
    laboratorista_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_asignadas',
        help_text="Laboratorista o técnico que acepta la solicitud"
    )

    # Estado actual en la máquina de estados del sistema
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE',
        help_text="Estado actual del flujo de trabajo"
    )

    # Enlace foráneo al catálogo de cultivos para calibrar el análisis
    cultivo_deseado_ref = models.ForeignKey(
        'cultivos.Cultivo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_asociadas',
        help_text="Enlace relacional al cultivo deseado en el catálogo maestro"
    )

    # Modalidad de prestación del servicio analítico
    modalidad = models.CharField(
        max_length=20,
        choices=MODALIDADES,
        default='VISITA',
        help_text="Modalidad de recolección de las muestras"
    )

    # Marcas cronológicas y observaciones de campo
    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de registro de la petición"
    )
    fecha_visita = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha programada por el laboratorista para la visita en finca"
    )
    notas_agricultor = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones iniciales del productor (historial de abonos, síntomas, etc.)"
    )

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Solicitud de Análisis'
        verbose_name_plural = 'Solicitudes de Análisis'

    @property
    def cultivo_deseado(self):
        """
        Propiedad de lectura para mantener compatibilidad con plantillas y APIs previas.

        Retorna:
            str: Nombre textual del cultivo referenciado o 'No especificado'.
        """
        return self.cultivo_deseado_ref.nombre if self.cultivo_deseado_ref else 'No especificado'

    @cultivo_deseado.setter
    def cultivo_deseado(self, value):
        """
        Setter polimórfico para asignar el cultivo deseado.

        Acepta una instancia de `Cultivo`, un identificador numérico o una cadena con su nombre común.
        """
        if not value:
            self.cultivo_deseado_ref = None
            return

        from apps.cultivos.models import Cultivo

        if isinstance(value, Cultivo):
            self.cultivo_deseado_ref = value
        elif str(value).isdigit():
            self.cultivo_deseado_ref = Cultivo.objects.filter(id=int(value)).first()
        else:
            self.cultivo_deseado_ref = Cultivo.objects.filter(nombre__icontains=str(value).strip()).first()

    def __str__(self):
        """Representación textual con ID, nombre de predio y estado visible."""
        return f"Solicitud #{self.id} - {self.terreno.nombre} ({self.get_estado_display()})"
