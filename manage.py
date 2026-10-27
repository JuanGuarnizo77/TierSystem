#!/usr/bin/env python
"""
Utilidad de Línea de Comandos para Tareas Administrativas de TierSystem.
========================================================================
Proporciona el punto de entrada principal para la ejecución de comandos
de gestión del ecosistema Django, incluyendo:
  - Servidor de desarrollo local (`runserver`).
  - Generación y aplicación de migraciones de base de datos (`makemigrations`, `migrate`).
  - Creación de cuentas maestras (`createsuperuser`).
  - Sembrado de datos de prueba y catálogos de Huila (`seed_mercado`, `seed_huila_completo`, etc.).
  - Ejecución de pruebas automatizadas (`test`).
"""

import os
import sys


def main():
    """
    Punto de entrada de ejecución para comandos administrativos de Django.

    Comportamiento:
      1. Asigna el módulo de configuración `tiersystem.settings` a las variables de entorno del sistema.
      2. Importa el ejecutor de comandos de Django de forma diferida para capturar
         errores de entorno virtual deshabilitado o faltante.
      3. Aplica una regla de ergonomía para el servidor de desarrollo: si se invoca `runserver`
         sin parámetros de host/puerto, enlaza automáticamente a `0.0.0.0:8000` para
         permitir pruebas desde dispositivos móviles en la misma red local Wi-Fi.
      4. Delega el control y los argumentos de consola a `execute_from_command_line`.
    """
    # Enlazar la configuración del proyecto
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiersystem.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está seguro de que está instalado y "
            "disponible en la variable de entorno PYTHONPATH? ¿Olvidó activar el "
            "entorno virtual de Python?"
        ) from exc

    # Si se ejecuta 'runserver' sin especificar dirección ni puerto, enlazar a 0.0.0.0:8000 por defecto
    # Esto facilita que laboratoristas y evaluadores prueben la PWA desde tabletas o celulares
    if len(sys.argv) == 2 and sys.argv[1] == 'runserver':
        sys.argv.append('0.0.0.0:8000')

    # Ejecutar el comando especificado por el usuario
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
