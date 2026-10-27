"""
Configuración WSGI para el Proyecto TierSystem.
==============================================
Expone la interfaz de invocable WSGI (Web Server Gateway Interface)
en la variable a nivel de módulo llamada `application`.

Permite que servidores web síncronos de producción (Gunicorn, uWSGI, Apache mod_wsgi,
o entornos en la nube como PythonAnywhere) canalicen peticiones HTTP hacia el framework Django.
"""

import os
from django.core.wsgi import get_wsgi_application

# Establecer la ruta del módulo de configuración principal de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiersystem.settings')

# Invocable estándar WSGI para el ciclo de vida de peticiones HTTP síncronas
application = get_wsgi_application()
