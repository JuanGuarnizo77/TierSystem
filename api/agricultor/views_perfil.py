"""
Módulo de Gestión de Perfil de Usuario y Seguridad para la API.
==============================================================
Proporciona endpoints REST protegidos por autenticación para la consulta y
actualización de los datos personales del usuario activo (nombre, correo,
teléfono) y el procedimiento seguro de cambio de contraseña con hashing PBKDF2.

Este controlador es transversal a cualquier usuario autenticado (agricultor,
laboratorista o administrador).
"""

from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def _datos_perfil(user):
    """
    Construye el payload canónico con la información de perfil del usuario.

    Parámetros:
        user (User): Instancia del modelo de usuario Django autenticado.

    Retorna:
        dict: Diccionario consolidado con credenciales básicas, datos del perfil
              asociado (`apps.usuarios.models.PerfilUsuario`) y marcas de auditoría.
    """
    perfil = getattr(user, 'perfil', None)
    return {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'nombre_completo': user.get_full_name() or user.username,
        'email': user.email,
        'telefono': perfil.telefono if perfil and perfil.telefono else '',
        'rol': perfil.rol if perfil else None,
        'date_joined': user.date_joined,
        'last_login': user.last_login,
    }


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def perfil_view(request):
    """
    GET /api/v1/perfil/
    -------------------
    Obtiene la información de perfil del usuario actualmente autenticado según su token JWT.

    PUT /api/v1/perfil/
    -------------------
    Actualiza la información personal del usuario autenticado:
      - Campos editables: `first_name`, `last_name`, `email`, `telefono`.
      - Valida la unicidad del correo electrónico evitando colisiones con otros usuarios.
      - Persiste modificaciones en el modelo `User` y en el modelo `PerfilUsuario` de forma segura.
    """
    user = request.user

    if request.method == 'PUT':
        # Sanitización y desinfección básica de espacios en blanco
        nombre = str(request.data.get('first_name', '')).strip()
        apellido = str(request.data.get('last_name', '')).strip()
        email = str(request.data.get('email', '')).strip()
        telefono = str(request.data.get('telefono', '')).strip()

        # Validación de unicidad de correo electrónico excluyendo la cuenta actual
        if email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response(
                    {'error': 'El correo electrónico ya está registrado por otro usuario.'},
                    status=400,
                )
            user.email = email

        # Actualización de nombres en la entidad principal User
        user.first_name = nombre
        user.last_name = apellido
        user.save()

        # Actualización del teléfono en la entidad relacionada Perfil
        if hasattr(user, 'perfil'):
            user.perfil.telefono = telefono
            user.perfil.save()

    return Response(_datos_perfil(user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cambiar_password_view(request):
    """
    POST /api/v1/perfil/password/
    -----------------------------
    Permite al usuario cambiar su clave de acceso mediante verificación de la clave actual.

    Cuerpo de la petición JSON:
      - `old_password`: Contraseña actual para validar identidad.
      - `new_password`: Nueva contraseña deseada (mínimo 6 caracteres).
      - `confirm_password`: Confirmación idéntica de la nueva contraseña.

    Seguridad:
      - Valida coincidencia entre `new_password` y `confirm_password`.
      - Valida longitud mínima de 6 caracteres.
      - Comprueba la validez de `old_password` mediante `user.check_password()`.
      - Realiza el hashing criptográfico de la nueva clave vía `user.set_password()`.
    """
    old_pass = request.data.get('old_password') or ''
    new_pass = request.data.get('new_password') or ''
    confirm_pass = request.data.get('confirm_password') or ''

    # Comprobación de consistencia en la confirmación
    if confirm_pass and new_pass != confirm_pass:
        return Response({'error': 'Las contraseñas nuevas no coinciden.'}, status=400)

    # Política de longitud mínima de contraseña
    if len(new_pass) < 6:
        return Response(
            {'error': 'La nueva contraseña debe tener al menos 6 caracteres.'},
            status=400,
        )

    user = request.user

    # Verificación criptográfica contra el hash almacenado en base de datos
    if not user.check_password(old_pass):
        return Response({'error': 'La contraseña actual es incorrecta.'}, status=400)

    # Aplicación del algoritmo PBKDF2 SHA-256 para la nueva contraseña y persistencia
    user.set_password(new_pass)
    user.save()
    return Response({'mensaje': 'Contraseña actualizada con éxito.'})