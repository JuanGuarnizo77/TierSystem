import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiersystem.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import PerfilUsuario

# Crear usuario admin
try:
    user = User.objects.create_superuser('admin', 'admin@tiersystem.com', 'admin123')
    user.first_name = "Super"
    user.last_name = "Admin"
    user.save()
    
    # Crear perfil
    PerfilUsuario.objects.create(user=user, rol='ADMIN')
    print("Administrador creado: admin / admin123")
except Exception as e:
    print("Error:", e)
