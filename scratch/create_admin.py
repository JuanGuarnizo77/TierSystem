"""
Script de Utilidad: Creación Rápida de Superusuario Administrador.
=================================================================
Permite aprovisionar de forma desatendida las credenciales maestras del sistema
para pruebas locales de desarrollo (`admin` / `admin123`).

Uso:
  python scratch/create_admin.py
"""

import os
import django

# Inicializar configuración del framework Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiersystem.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Perfil

# Creación idempotente del superusuario maestro
try:
    if not User.objects.filter(username='admin').exists():
        # Generar superusuario con permisos totales en Django Auth y Admin
        user = User.objects.create_superuser('admin', 'admin@tiersystem.com', 'admin123')
        user.first_name = "Super"
        user.last_name = "Admin"
        user.save()

        # El signal `post_save` crea automáticamente la instancia Perfil; actualizamos su rol a 'ADMIN'
        user.perfil.rol = 'ADMIN'
        user.perfil.save()
        print("Administrador creado exitosamente: admin / admin123")
    else:
        print("El usuario 'admin' ya se encuentra registrado en el sistema.")
except Exception as e:
    print("Error durante la creación del superusuario:", e)
