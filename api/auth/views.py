"""
Controladores de Autenticación JWT y Gestión de Cuentas - TierSystem API.
Implementa el flujo stateless para aplicaciones móviles (Flutter) utilizando
JSON Web Tokens (Access Token a 8 horas, Refresh Token a 30 días).
"""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import UsuarioSerializer, RegistroSerializer


class TierSystemTokenSerializer(TokenObtainPairSerializer):
    """
    Personalización del serializador de inicio de sesión JWT de SimpleJWT.
    Inyecta el objeto del usuario serializado ('user') dentro de la misma respuesta
    del login para que la aplicación móvil configure de inmediato el estado
    y menú correspondiente sin requerir una segunda petición HTTP hacia /me/.
    """
    def validate(self, attrs):
        # Valida credenciales contra el backend de autenticación de Django
        data = super().validate(attrs)
        # Inyecta los datos de perfil y rol en la carga útil de respuesta
        user = self.user
        data['user'] = UsuarioSerializer(user).data
        return data


class LoginView(TokenObtainPairView):
    """
    Endpoint de Autenticación de Credenciales.
    POST /api/v1/auth/login/
    Recibe username y password; valida contra auth_user y devuelve par de tokens JWT (access y refresh)
    junto con la estructura de perfil del usuario autenticado.
    """
    serializer_class = TierSystemTokenSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Endpoint de Verificación de Sesión Activa.
    GET /api/v1/auth/me/
    Cabecera requerida: Authorization: Bearer <access_token>
    Retorna la información consolidada del usuario extraída a partir de su token JWT.
    """
    # Serializa la instancia de User asociada a la firma del token recibido
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def registro_view(request):
    """
    Endpoint de Registro Público para Agricultores.
    POST /api/v1/auth/registro/
    Body JSON: { username, email, first_name, last_name, password, password2, telefono (opcional) }
    Crea la cuenta, asigna rol 'AGRICULTOR' y expide automáticamente el par de tokens JWT
    para inicio de sesión transparente inmediato.
    """
    # Valida integridad sintáctica, fortaleza de contraseña y unicidad de email
    serializer = RegistroSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Persistencia en base de datos
    user = serializer.save()

    # Emisión criptográfica inmediata de credenciales JWT
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "mensaje": "Cuenta creada exitosamente.",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UsuarioSerializer(user).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Endpoint de Cierre de Sesión.
    POST /api/v1/auth/logout/
    Body JSON: { "refresh": "<refresh_token>" }
    Valida la estructura del refresh token para invalidación en el cliente móvil.
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({"error": "Se requiere el refresh token."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Instancia el token para verificar que sea sintáctica y criptográficamente válido
        RefreshToken(refresh_token)
        return Response({"mensaje": "Sesión cerrada correctamente."})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

