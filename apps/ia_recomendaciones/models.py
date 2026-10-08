from django.db import models

class CultivoIdeal(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    # Rangos óptimos
    humedad_min = models.FloatField()
    humedad_max = models.FloatField()
    
    temperatura_min = models.FloatField()
    temperatura_max = models.FloatField()
    
    conductividad_min = models.FloatField()
    conductividad_max = models.FloatField()
    
    ph_min = models.FloatField()
    ph_max = models.FloatField()
    
    nitrogeno_min = models.FloatField()
    nitrogeno_max = models.FloatField()
    
    fosforo_min = models.FloatField()
    fosforo_max = models.FloatField()
    
    potasio_min = models.FloatField()
    potasio_max = models.FloatField()

    def __str__(self):
        return self.nombre

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "rangos": {
                "humedad": [self.humedad_min, self.humedad_max],
                "temperatura": [self.temperatura_min, self.temperatura_max],
                "conductividad": [self.conductividad_min, self.conductividad_max],
                "ph": [self.ph_min, self.ph_max],
                "nitrogeno": [self.nitrogeno_min, self.nitrogeno_max],
                "fosforo": [self.fosforo_min, self.fosforo_max],
                "potasio": [self.potasio_min, self.potasio_max]
            }
        }

class ConfiguracionGlobal(models.Model):
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
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Configuración Global del Sistema"
