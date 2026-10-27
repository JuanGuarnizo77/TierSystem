"""
Configuración de la Aplicación de Cultivos en Django.
====================================================
Establece los metadatos y la inicialización del módulo de catálogo agrícola.
"""

from django.apps import AppConfig


class CultivosConfig(AppConfig):
    """Metadatos de la aplicación de cultivos del Huila."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cultivos'
    verbose_name = 'Catálogo de Cultivos del Huila'
