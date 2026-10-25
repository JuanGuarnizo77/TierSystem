"""
Configuración de la Aplicación SIPSA en Django.
==============================================
Establece los metadatos y la inicialización del módulo de reportes SIPSA/DANE.
"""

from django.apps import AppConfig


class SipsaConfig(AppConfig):
    """Metadatos de la aplicación de reportes y predicción de precios SIPSA."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sipsa'
    verbose_name = 'Reportes SIPSA/DANE'
