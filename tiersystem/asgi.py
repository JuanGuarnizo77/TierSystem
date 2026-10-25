"""
Configuración ASGI para el Proyecto TierSystem.
==============================================
Expone la interfaz de invocable ASGI (Asynchronous Server Gateway Interface)
en la variable a nivel de módulo llamada `application`.

Permite la ejecución del servidor web en servidores y pasarelas compatibles
con protocolos asíncronos (Uvicorn, Daphne) para soportar WebSockets, eventos
en tiempo real o conexiones telemétricas concurrentes de sensores IoT.
"""

import os
from django.core.asgi import get_asgi_application

# Establecer la ruta del módulo de configuración principal de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiersystem.settings')

# Invocable estándar ASGI para gestión de peticiones asíncronas
application = get_asgi_application()
