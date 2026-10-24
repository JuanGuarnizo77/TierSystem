from django.db import models

class Cultivo(models.Model):
    """
    Catálogo Maestro Universal de Cultivos del Departamento del Huila.
    Entidad canónica de la cual se desprenden los terrenos, solicitudes,
    diagnósticos de IA, precios SIPSA y consultas offline.
    """
    # Identificación y Taxonomía
    nombre = models.CharField(max_length=120, unique=True, help_text="Nombre común o variedad (ej. Café Castillo, Cacao, Cholupa)")
    nombre_cientifico = models.CharField(max_length=150, blank=True, default='', help_text="Nombre científico botánico")
    categoria = models.CharField(max_length=80, default='Frutal', help_text="Frutal, Cereal, Tubérculo, Leguminosa, Hortaliza, Industrial, etc.")
    clima = models.CharField(max_length=80, default='Templado', help_text="Cálido, Templado, Frío, Tropical, etc.")
    icono = models.CharField(max_length=60, default='fa-seedling', help_text="Clase FontAwesome (ej. fa-mug-hot, fa-lemon)")
    descripcion = models.TextField(blank=True, default='', help_text="Descripción agronómica y aptitud productiva en el Huila")
    
    # Pisos Altitudinales Óptimos (msnm - metros sobre el nivel del mar)
    altitud_min = models.DecimalField(max_digits=7, decimal_places=2, default=0, help_text="Altitud mínima recomendada en msnm")
    altitud_max = models.DecimalField(max_digits=7, decimal_places=2, default=3000, help_text="Altitud máxima recomendada en msnm")
    
    # Rangos Edafológicos Óptimos (Calibración IA / Diagnóstico de Suelos)
    ph_min = models.DecimalField(max_digits=4, decimal_places=2, default=5.5)
    ph_max = models.DecimalField(max_digits=4, decimal_places=2, default=6.8)
    
    humedad_min = models.DecimalField(max_digits=5, decimal_places=2, default=60.0)
    humedad_max = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)
    
    temperatura_min = models.DecimalField(max_digits=5, decimal_places=2, default=18.0)
    temperatura_max = models.DecimalField(max_digits=5, decimal_places=2, default=26.0)
    
    conductividad_min = models.DecimalField(max_digits=8, decimal_places=2, default=0.8)
    conductividad_max = models.DecimalField(max_digits=8, decimal_places=2, default=2.2)
    
    nitrogeno_min = models.DecimalField(max_digits=6, decimal_places=2, default=120.0, help_text="mg/kg")
    nitrogeno_max = models.DecimalField(max_digits=6, decimal_places=2, default=250.0, help_text="mg/kg")
    
    fosforo_min = models.DecimalField(max_digits=6, decimal_places=2, default=25.0, help_text="mg/kg")
    fosforo_max = models.DecimalField(max_digits=6, decimal_places=2, default=65.0, help_text="mg/kg")
    
    potasio_min = models.DecimalField(max_digits=6, decimal_places=2, default=140.0, help_text="mg/kg")
    potasio_max = models.DecimalField(max_digits=6, decimal_places=2, default=280.0, help_text="mg/kg")
    
    # Enlace canónico SIPSA/DANE y estado operativo
    nombre_dane = models.CharField(max_length=120, blank=True, default='', help_text="Nombre homologado en reportes DANE")
    activo = models.BooleanField(default=True, help_text="Visible en catálogo y selección de diagnósticos")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Cultivo'
        verbose_name_plural = 'Cultivos'
        db_table = 'cultivos_cultivo'

    def __str__(self):
        return f"{self.nombre} ({self.categoria})"

    def to_dict(self):
        """Retorna diccionario estructurado para consumo de APIs y motor de IA."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "clima": self.clima,
            "icono": self.icono,
            "descripcion": self.descripcion,
            "rangos": {
                "ph": [float(self.ph_min), float(self.ph_max)],
                "humedad": [float(self.humedad_min), float(self.humedad_max)],
                "temperatura": [float(self.temperatura_min), float(self.temperatura_max)],
                "conductividad": [float(self.conductividad_min), float(self.conductividad_max)],
                "nitrogeno": [float(self.nitrogeno_min), float(self.nitrogeno_max)],
                "fosforo": [float(self.fosforo_min), float(self.fosforo_max)],
                "potasio": [float(self.potasio_min), float(self.potasio_max)],
                "altitud": [float(self.altitud_min), float(self.altitud_max)],
            }
        }

    def to_catalogo_dict(self):
        """Formato amigable para tarjetas en frontend web y PWA."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "clima": self.clima,
            "ph": f"{float(self.ph_min):.1f} - {float(self.ph_max):.1f}",
            "humedad": f"{int(self.humedad_min)}% - {int(self.humedad_max)}%",
            "img": self.icono,
            "descripcion": self.descripcion,
            "altitud": f"{int(self.altitud_min)} - {int(self.altitud_max)} msnm",
            "altitud_min": float(self.altitud_min),
            "altitud_max": float(self.altitud_max),
            "nitrogeno": f"{int(self.nitrogeno_min)} - {int(self.nitrogeno_max)} mg/kg",
            "fosforo": f"{int(self.fosforo_min)} - {int(self.fosforo_max)} mg/kg",
            "potasio": f"{int(self.potasio_min)} - {int(self.potasio_max)} mg/kg",
        }
