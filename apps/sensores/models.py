from django.db import models

class LecturaSensor(models.Model):
    humedad = models.FloatField()
    temperatura = models.FloatField()
    conductividad = models.FloatField()
    ph = models.FloatField()
    nitrogeno = models.FloatField()
    fosforo = models.FloatField()
    potasio = models.FloatField()
    
    # Campo para registrar cuándo llegó el dato exacto (útil para el filtro de 20s)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Lectura {self.id} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
