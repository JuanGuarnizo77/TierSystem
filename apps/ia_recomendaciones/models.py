from django.db import models


class ConfiguracionGlobal(models.Model):
    """Configuración global de comportamiento IA y umbrales globales de sensores."""
    # US-0039: Comportamiento IA
    tiempo_espera_ia = models.IntegerField(default=30, help_text="Tiempo máximo de espera (segundos)")
    accion_fallo_ia = models.CharField(max_length=50, choices=[
        ('DB_LOCAL', 'Usar base de datos local automáticamente'),
        ('CANCELAR', 'Notificar al usuario y cancelar el análisis')
    ], default='DB_LOCAL')
    
    # US-0038: Rangos globales del sensor
    rango_ph_min = models.FloatField(default=0.0)
    rango_ph_max = models.FloatField(default=14.0)
    
    rango_n_min = models.FloatField(default=0.0)
    rango_n_max = models.FloatField(default=1000.0)
    
    rango_p_min = models.FloatField(default=0.0)
    rango_p_max = models.FloatField(default=1000.0)
    
    rango_k_min = models.FloatField(default=0.0)
    rango_k_max = models.FloatField(default=1000.0)
    
    rango_humedad_min = models.FloatField(default=0.0)
    rango_humedad_max = models.FloatField(default=100.0)
    
    rango_ce_min = models.FloatField(default=0.0)
    rango_ce_max = models.FloatField(default=20.0)
    
    rango_temp_min = models.FloatField(default=-10.0)
    rango_temp_max = models.FloatField(default=60.0)

    class Meta:
        verbose_name = 'Configuración Global'
        verbose_name_plural = 'Configuraciones Globales'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Configuración Global del Sistema"
