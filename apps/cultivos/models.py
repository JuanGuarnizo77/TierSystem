"""
Modelo de Dominio: Catálogo Maestro de Cultivos del Departamento del Huila.
============================================================================
Define la entidad `Cultivo`, pieza fundamental del sistema agroecológico de
TierSystem. Contiene la taxonomía, adaptación agroclimática (pisos altitudinales)
y la parametrización fisicoquímica edafológica (pH, conductividad eléctrica,
humedad, temperatura y macronutrientes N-P-K).

Estos rangos alimentan:
  1. El motor algorítmico de compatibilidad edáfica (`apps.ia_recomendaciones`).
  2. Las reglas de validación en campo para muestreo sensorizado (`apps.sensores`).
  3. La homologación de precios agrícolas con SIPSA/DANE (`apps.sipsa`).
  4. La base de datos local en IndexedDB (Dexie.js) para funcionamiento offline.
"""

from django.db import models


class Cultivo(models.Model):
    """
    Entidad canónica que representa una especie o variedad agrícola en el Huila.

    Almacena los umbrales mínimos y máximos ideales para cada variable física
    y química del suelo. Es utilizada por los evaluadores heurísticos y por los
    prompts estructurados de los modelos de inteligencia artificial.
    """

    # =========================================================================
    # Identificación Botánica, Taxonómica y Agroecológica
    # =========================================================================
    nombre = models.CharField(
        max_length=120,
        unique=True,
        help_text="Nombre común o variedad comercial (ej. Café Castillo, Cacao CCN-51, Cholupa del Huila)"
    )
    nombre_cientifico = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text="Nombre científico botánico estandarizado (ej. Coffea arabica)"
    )
    categoria = models.CharField(
        max_length=80,
        default='Frutal',
        help_text="Clasificación agroproductiva (Frutal, Cereal, Tubérculo, Leguminosa, Hortaliza, Industrial, etc.)"
    )
    clima = models.CharField(
        max_length=80,
        default='Templado',
        help_text="Aptitud bioclimática predominante (Cálido, Templado, Frío, Tropical)"
    )
    icono = models.CharField(
        max_length=60,
        default='fa-seedling',
        help_text="Clase CSS de FontAwesome para representación visual (ej. fa-mug-hot, fa-lemon, fa-apple-whole)"
    )
    descripcion = models.TextField(
        blank=True,
        default='',
        help_text="Resumen agronómico, comportamiento fisiológico y condiciones óptimas en el Huila"
    )

    # =========================================================================
    # Zonificación Altitudinal (msnm - Metros Sobre el Nivel del Mar)
    # =========================================================================
    altitud_min = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text="Piso altitudinal inferior recomendado en msnm"
    )
    altitud_max = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=3000,
        help_text="Piso altitudinal superior recomendado en msnm"
    )

    # =========================================================================
    # Rangos Fisicoquímicos y Nutricionales Óptimos del Suelo
    # =========================================================================
    # Potencial de Hidrógeno (pH) en escala estándar de 0 a 14
    ph_min = models.DecimalField(max_digits=4, decimal_places=2, default=5.5)
    ph_max = models.DecimalField(max_digits=4, decimal_places=2, default=6.8)

    # Humedad volumétrica del suelo en porcentaje (%)
    humedad_min = models.DecimalField(max_digits=5, decimal_places=2, default=60.0)
    humedad_max = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)

    # Temperatura edáfica en grados Celsius (°C)
    temperatura_min = models.DecimalField(max_digits=5, decimal_places=2, default=18.0)
    temperatura_max = models.DecimalField(max_digits=5, decimal_places=2, default=26.0)

    # Conductividad Eléctrica (CE) en dS/m o mS/cm (salinidad del suelo)
    conductividad_min = models.DecimalField(max_digits=8, decimal_places=2, default=0.8)
    conductividad_max = models.DecimalField(max_digits=8, decimal_places=2, default=2.2)

    # Nitrógeno disponible (N) en miligramos por kilogramo (mg/kg o ppm)
    nitrogeno_min = models.DecimalField(max_digits=6, decimal_places=2, default=120.0, help_text="mg/kg")
    nitrogeno_max = models.DecimalField(max_digits=6, decimal_places=2, default=250.0, help_text="mg/kg")

    # Fósforo disponible (P) por método Bray II / Mehlich en mg/kg
    fosforo_min = models.DecimalField(max_digits=6, decimal_places=2, default=25.0, help_text="mg/kg")
    fosforo_max = models.DecimalField(max_digits=6, decimal_places=2, default=65.0, help_text="mg/kg")

    # Potasio intercambiable (K) en mg/kg
    potasio_min = models.DecimalField(max_digits=6, decimal_places=2, default=140.0, help_text="mg/kg")
    potasio_max = models.DecimalField(max_digits=6, decimal_places=2, default=280.0, help_text="mg/kg")

    # =========================================================================
    # Homologación SIPSA/DANE y Ciclo de Vida
    # =========================================================================
    nombre_dane = models.CharField(
        max_length=120,
        blank=True,
        default='',
        help_text="Nombre oficial homologado en el boletín semanal SIPSA del DANE"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el cultivo está disponible en catálogos y formularios de solicitud"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Cultivo'
        verbose_name_plural = 'Cultivos'
        db_table = 'cultivos_cultivo'

    def __str__(self):
        """Representación textual formal del cultivo y su categoría productiva."""
        return f"{self.nombre} ({self.categoria})"

    def to_dict(self):
        """
        Serializa el cultivo a un diccionario con tipos nativos de Python.

        Especialmente formateado para la inyección de contexto en motores
        heurísticos, árboles de decisión y sincronización offline en IndexedDB.

        Retorna:
            dict: Estructura jerárquica con metadatos y tuplas [min, max] de rangos.
        """
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
        """
        Serializa el cultivo con cadenas de texto formateadas y unidades de medida.

        Diseñado específicamente para el renderizado inmediato en tarjetas de UI
        (interfaz web de escritorio y aplicación móvil PWA), evitando lógica de
        formateo en los componentes de vista.

        Retorna:
            dict: Cadenas de presentación con unidades para cada parámetro edáfico.
        """
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
