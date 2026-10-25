"""
Configuración de la Aplicación API REST Móvil de TierSystem.
============================================================
Declara los metadatos y ciclo de vida de la aplicación Django `api`,
encargada de centralizar los endpoints RESTful para la aplicación móvil,
incluyendo autenticación por JWT, gestión de fincas, solicitudes de análisis,
consulta de catálogos y sincronización de datos fuera de línea.
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """
    Configuración de la aplicación API RESTful.

    Atributos:
      - `default_auto_field`: Define el tipo de clave primaria por defecto.
      - `name`: Nombre del paquete Python que representa la aplicación.
      - `verbose_name`: Nombre legible en el panel administrativo.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = 'API REST Móvil'
