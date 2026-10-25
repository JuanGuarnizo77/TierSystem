"""
Script de Sembrado: Generación Rápida de Usuarios de Prueba.
============================================================
Crea de manera desatendida las cuentas de prueba para cada rol de usuario del sistema:
  - Administrador: `admin` / `admin123` (Rol: ADMIN)
  - Laboratorista: `lab` / `lab123` (Rol: LABORATORISTA)

Uso:
  python scratch/seed_users.py
"""

import os
import sys
import django

# Asegurar que el directorio raíz del proyecto forme parte de sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiersystem.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Perfil


def create_user(username, password, rol):
    """
    Crea o valida un usuario en la base de datos con el rol especificado.

    Parámetros:
      - `username` (str): Nombre de usuario único.
      - `password` (str): Contraseña sin cifrar (se almacena cifrada mediante Django Auth).
      - `rol` (str): Rol agronómico ('ADMIN', 'LABORATORISTA', 'AGRICULTOR').
    """
    if not User.objects.filter(username=username).exists():
        # Creación del registro base de autenticación en la tabla auth_user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=f"{username}@tiersystem.local"
        )
        # El signal post_save crea el perfil automáticamente con rol AGRICULTOR; lo reasignamos
        user.perfil.rol = rol
        user.perfil.save()
        print(f"Usuario creado exitosamente: {username} (Rol: {rol})")
    else:
        print(f"El usuario '{username}' ya existe en la base de datos.")


if __name__ == '__main__':
    print("Inicializando usuarios de prueba del ecosistema TierSystem...")
    create_user('admin', 'admin123', 'ADMIN')
    create_user('lab', 'lab123', 'LABORATORISTA')
    print("Proceso de inicialización de usuarios finalizado.")
