from django.db import models

class CultivoIdeal(models.Model):
    # NOTE: El valor de este campo debe coincidir con CultivoSipsa.nombre del catálogo
    # canónico (apps/sipsa). No hay FK directa para evitar dependencia de esquema,
    # pero los nombres deben mantenerse sincronizados manualmente.
    nombre = models.CharField(
        max_length=100, unique=True,
        help_text="Debe coincidir con CultivoSipsa.nombre del catálogo canónico",
    )
    descripcion = models.TextField(blank=True, null=True)
    
    # Clasificación y presentación
    categoria = models.CharField(max_length=80, default='Frutal', blank=True, help_text="Frutal, Cereal, Tubérculo, Leguminosa, Hortaliza, Industrial, etc.")
    clima = models.CharField(max_length=80, default='Templado', blank=True, help_text="Cálido, Templado, Frío, Tropical, etc.")
    icono = models.CharField(max_length=60, default='fa-seedling', help_text="Clase FontAwesome, ej. fa-mug-hot, fa-lemon")
    
    # Altitud agronómica óptima (msnm)
    altitud_min = models.DecimalField(max_digits=7, decimal_places=2, default=0, help_text="Altitud mínima óptima en msnm")
    altitud_max = models.DecimalField(max_digits=7, decimal_places=2, default=3000, help_text="Altitud máxima óptima en msnm")
    
    # Enlace canónico y estado
    nombre_dane = models.CharField(max_length=120, blank=True, default='', help_text="Nombre correspondiente en SIPSA/DANE")
    activo = models.BooleanField(default=True)
    
    # Rangos óptimos edafológicos
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

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Cultivo Ideal'
        verbose_name_plural = 'Cultivos Ideales'

    def __str__(self):
        return self.nombre

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "clima": self.clima,
            "icono": self.icono,
            "descripcion": self.descripcion,
            "rangos": {
                "humedad": [self.humedad_min, self.humedad_max],
                "temperatura": [self.temperatura_min, self.temperatura_max],
                "conductividad": [self.conductividad_min, self.conductividad_max],
                "ph": [self.ph_min, self.ph_max],
                "nitrogeno": [self.nitrogeno_min, self.nitrogeno_max],
                "fosforo": [self.fosforo_min, self.fosforo_max],
                "potasio": [self.potasio_min, self.potasio_max],
                "altitud": [float(self.altitud_min or 0), float(self.altitud_max or 3000)],
            }
        }

    def to_catalogo_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "categoria": self.categoria or "Frutal",
            "clima": self.clima or "Templado",
            "ph": f"{self.ph_min:.1f} - {self.ph_max:.1f}",
            "humedad": f"{int(self.humedad_min)}% - {int(self.humedad_max)}%",
            "img": self.icono or "fa-seedling",
            "descripcion": self.descripcion or "",
            "altitud_min": float(self.altitud_min or 0),
            "altitud_max": float(self.altitud_max or 3000),
            "altitud": f"{int(self.altitud_min or 0)} - {int(self.altitud_max or 3000)} msnm",
            "nitrogeno": f"{int(self.nitrogeno_min)} - {int(self.nitrogeno_max)} mg/kg",
            "fosforo": f"{int(self.fosforo_min)} - {int(self.fosforo_max)} mg/kg",
            "potasio": f"{int(self.potasio_min)} - {int(self.potasio_max)} mg/kg",
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
