import os
import sys
import django

# Add the project directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiersystem.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Perfil

def create_user(username, password, rol):
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, password=password, email=f"{username}@tiersystem.local")
        # El signal crea el perfil automáticamente con rol AGRICULTOR
        user.perfil.rol = rol
        user.perfil.save()
        print(f"Usuario creado: {username} (Rol: {rol})")
    else:
        print(f"Usuario {username} ya existe.")

print("Inicializando usuarios de prueba...")
create_user('admin', 'admin123', 'ADMIN')
create_user('lab', 'lab123', 'LABORATORISTA')
print("Proceso finalizado.")
