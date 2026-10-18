from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def _datos_perfil(user):
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
    GET /api/v1/perfil/  -> datos del usuario autenticado
    PUT /api/v1/perfil/  -> actualiza first_name, last_name, email, telefono
    """
    user = request.user

    if request.method == 'PUT':
        nombre = str(request.data.get('first_name', '')).strip()
        apellido = str(request.data.get('last_name', '')).strip()
        email = str(request.data.get('email', '')).strip()
        telefono = str(request.data.get('telefono', '')).strip()

        if email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response(
                    {'error': 'El correo electrónico ya está registrado por otro usuario.'},
                    status=400,
                )
            user.email = email

        user.first_name = nombre
        user.last_name = apellido
        user.save()

        if hasattr(user, 'perfil'):
            user.perfil.telefono = telefono
            user.perfil.save()

    return Response(_datos_perfil(user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cambiar_password_view(request):
    """
    POST /api/v1/perfil/password/
    Body: { "old_password", "new_password", "confirm_password" }
    """
    old_pass = request.data.get('old_password') or ''
    new_pass = request.data.get('new_password') or ''
    confirm_pass = request.data.get('confirm_password') or ''

    if confirm_pass and new_pass != confirm_pass:
        return Response({'error': 'Las contraseñas nuevas no coinciden.'}, status=400)

    if len(new_pass) < 6:
        return Response(
            {'error': 'La nueva contraseña debe tener al menos 6 caracteres.'},
            status=400,
        )

    user = request.user
    if not user.check_password(old_pass):
        return Response({'error': 'La contraseña actual es incorrecta.'}, status=400)

    user.set_password(new_pass)
    user.save()
    return Response({'mensaje': 'Contraseña actualizada con éxito.'})