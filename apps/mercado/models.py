"""
Modelo de Dominio: Directorio de Compradores y Canales de Comercialización.
===========================================================================
Modela los actores comerciales del sector agropecuario en el departamento del Huila:
cooperativas agrícolas (ej. CADEFIHUILA, COOPECSILLAS), plazas mayoristas (Surabastos),
asociaciones de productores (Asohofrucol) e intermediarios y exportadores regionales.

Vincula a los compradores con las especies vegetales de su interés (`cultivos_rel`)
para sugerir canales directos de venta al productor tras finalizar su análisis de suelo.
"""

from django.db import models


class Comprador(models.Model):
    """
    Entidad comercial que representa un comprador o centro de acopio agropecuario.

    Atributos:
        nombre (CharField): Razón social o denominación comercial de la empresa.
        tipo (CharField): Clasificación (Cooperativa, Plaza de Mercado, Intermediario, Exportador).
        municipio (CharField): Ubicación del centro de acopio o sede en el Huila.
        contacto (CharField): Línea telefónica principal.
        cultivos_rel (ManyToManyField): Relación muchos a muchos con el catálogo maestro de cultivos.
        precio_referencia (CharField): Frase o rango de compra de referencia (ej. "$1.460 / kg").
        activo (BooleanField): Bandera de visibilidad en el directorio.
        email (EmailField): Correo de contacto comercial.
        whatsapp (CharField): Enlace directo para mensajería móvil instantánea.
        sitio_web (CharField): Portal web institucional.
    """
    nombre = models.CharField(
        max_length=150,
        help_text="Razón social o nombre del comprador"
    )
    tipo = models.CharField(
        max_length=50,
        help_text="Tipo de comprador (Cooperativa, Plaza de Mercado, Intermediario, Exportador)"
    )
    municipio = models.CharField(
        max_length=100,
        default='Neiva, Huila',
        help_text="Municipio o centro logístico en el Huila"
    )
    contacto = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Teléfono de contacto comercial"
    )
    cultivos_rel = models.ManyToManyField(
        'cultivos.Cultivo',
        blank=True,
        related_name='compradores_interesados',
        help_text="Cultivos de interés vinculados relacionalmente con el catálogo maestro"
    )
    precio_referencia = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Precio de referencia ofrecido en plaza (ej. '$18.200 / arroba')"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el comprador está habilitado para ser recomendado"
    )
    email = models.EmailField(
        blank=True,
        default='',
        help_text="Correo electrónico para remisión de cotizaciones"
    )
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text="Número telefónico para apertura de chat de WhatsApp"
    )
    sitio_web = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="URL del sitio web del comprador"
    )

    class Meta:
        verbose_name = 'Comprador'
        verbose_name_plural = 'Compradores'
        ordering = ['nombre']

    def __str__(self):
        """Identificador textual del comprador."""
        return self.nombre

    @property
    def cultivos_interes(self):
        """
        Propiedad de compatibilidad hacia atrás que retorna los nombres separados por coma.

        Retorna:
            str: Lista de nombres de cultivos en texto plano o 'Varios cultivos'.
        """
        nombres = [c.nombre for c in self.cultivos_rel.all()]
        return ", ".join(nombres) if nombres else "Varios cultivos"
