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
