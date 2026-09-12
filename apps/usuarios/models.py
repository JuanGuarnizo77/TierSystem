from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Perfil(models.Model):
    ROL_CHOICES = (
        ('AGRICULTOR', 'Agricultor'),
        ('LABORATORISTA', 'Laboratorista'),
        ('ADMIN', 'Administrador'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='AGRICULTOR')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_rol_display()}"

# Signal para crear el perfil automáticamente cuando se crea un User (por si acaso se crean desde el admin)
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    instance.perfil.save()
