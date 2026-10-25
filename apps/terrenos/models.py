"""
Modelo de Dominio: Predios y Terrenos Agrícolas.
================================================
Gestiona las parcelas, fincas y lotes agrícolas de los productores en el Huila.
Registra la ubicación geográfica (vereda/municipio), extensión superficial
en hectáreas, altitud media sobre el nivel del mar, delimitación perimetral
en formato GeoJSON para mapas interactivos y vínculo al cultivo establecido.
"""

from django.db import models
from django.contrib.auth.models import User


class Terreno(models.Model):
    """
    Representa una finca o lote productivo perteneciente a un agricultor.

    Es la unidad espacial primaria donde se solicitan los análisis de suelo,
    se programan las rutas de muestreo y se calculan las densidades de puntos sensorizados.
    """
    # Propietario del predio (aislamiento multi-inquilino)
    agricultor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='terrenos',
        help_text="Productor agrícola propietario del predio"
    )

    # Identificación y ubicación administrativa
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre de la finca o lote (ej. Finca La Esperanza, Lote El Mirador)"
    )
    ubicacion = models.CharField(
        max_length=255,
        help_text="Ubicación geográfica descriptiva (ej. Vereda Bajo San Francisco, Pitalito)"
    )

    # Extensión territorial en hectáreas (base para la densidad de muestreo)
    hectareas = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Área superficial del terreno en hectáreas (mínimo 0.01 ha)"
    )

    # Relación de clave foránea con el catálogo maestro de cultivos
    cultivo_ref = models.ForeignKey(
        'cultivos.Cultivo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='terrenos',
        help_text="Enlace relacional al cultivo establecido o planificado en el catálogo maestro"
    )

    # Variables fisiográficas y espaciales
    altitud_promedio = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Altitud promedio sobre el nivel del mar (msnm) calculada por GPS o elevación digital"
    )
    coordenadas_poligono = models.TextField(
        blank=True,
        null=True,
        help_text="Estructura serializada GeoJSON con las coordenadas de los vértices del polígono"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Marca temporal de creación del registro en el sistema"
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Terreno'
        verbose_name_plural = 'Terrenos'

    @property
    def cultivo_principal(self):
        """
        Propiedad de lectura para mantener compatibilidad hacia atrás con vistas y plantillas.

        Retorna:
            str: Nombre textual del cultivo referenciado o 'No especificado'.
        """
        return self.cultivo_ref.nombre if self.cultivo_ref else 'No especificado'

    @cultivo_principal.setter
    def cultivo_principal(self, value):
        """
        Setter polimórfico que resuelve y enlaza una entidad `Cultivo`.

        Acepta:
          - Una instancia directa del modelo `Cultivo`.
          - Un identificador numérico entero o string de dígitos (`id`).
          - Una cadena de texto con el nombre común del cultivo (búsqueda insensible a mayúsculas).
        """
        if not value:
            self.cultivo_ref = None
            return

        from apps.cultivos.models import Cultivo

        if isinstance(value, Cultivo):
            self.cultivo_ref = value
        elif str(value).isdigit():
            self.cultivo_ref = Cultivo.objects.filter(id=int(value)).first()
        else:
            self.cultivo_ref = Cultivo.objects.filter(nombre__icontains=str(value).strip()).first()

    def __str__(self):
        """Representación textual para listados y depuración."""
        return f"{self.nombre} ({self.agricultor.username})"
