"""
Modelo de Dominio: Perfil de Usuario y Control de Acceso por Roles (RBAC).
==========================================================================
Extiende el modelo de autenticación estándar de Django (`User`) mediante una
relación uno a uno (`OneToOneField`), asignando a cada cuenta un rol del
sistema ('AGRICULTOR', 'LABORATORISTA', 'ADMIN') y atributos de contacto.

Incluye receptores de señales (`signals`) para la creación e hidratación
automática del perfil tras la persistencia de un nuevo usuario.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Perfil(models.Model):
    """
    Extensión del modelo de usuario Django para la gestión de roles en TierSystem.

    Atributos:
        user (OneToOneField): Vínculo directo en cascada con la entidad de autenticación base.
        rol (CharField): Rol funcional que define permisos de navegación, acceso a vistas
                         y autorización en la API REST.
        telefono (CharField): Línea móvil o de contacto del productor o técnico.
    """
    # Matriz de roles del sistema
    ROL_CHOICES = (
        ('AGRICULTOR', 'Agricultor'),
        ('LABORATORISTA', 'Laboratorista'),
        ('ADMIN', 'Administrador'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil',
        help_text="Usuario del sistema al que pertenece este perfil"
    )
    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default='AGRICULTOR',
        help_text="Rol operativo que determina las vistas y permisos disponibles"
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Número de teléfono móvil o contacto principal"
    )

    def __str__(self):
        """Representación textual para auditoría y administración."""
        return f"{self.user.username} - {self.get_rol_display()}"


# =============================================================================
# Señales del Ciclo de Vida (Lifecycle Signals)
# =============================================================================

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Señal post-save: Inicializa automáticamente el perfil asociado al crear un User.

    Garantiza que cualquier usuario creado desde la consola, el panel administrativo
    o el registro web disponga de un registro `Perfil` con rol predeterminado.
    """
    if created:
        Perfil.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, created, **kwargs):
    """
    Señal post-save: Sincroniza y almacena el perfil cuando el User es modificado.

    Previene inconsistencias de persistencia asegurando que cambios en la entidad
    principal se reflejen en la relación uno a uno.
    """
    if not created and hasattr(instance, 'perfil'):
        instance.perfil.save()
