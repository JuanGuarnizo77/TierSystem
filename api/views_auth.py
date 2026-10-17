from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import UsuarioSerializer, RegistroSerializer


# ---------------------------------------------------------------------------
# JWT personalizado: agrega rol y nombre al payload del token
# ---------------------------------------------------------------------------

class TierSystemTokenSerializer(TokenObtainPairSerializer):
    """
    Extiende el login JWT estándar para devolver, además de los tokens,
    los datos básicos del usuario (rol, nombre) para que Flutter los use
    sin necesidad de llamar a /me/ por separado.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user
        data['user'] = UsuarioSerializer(user).data
        return data


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: { "username": "...", "password": "..." }
    Response:
    {
        "access": "<jwt>",
        "refresh": "<jwt>",
        "user": { "id", "username", "email", "nombre_completo", "perfil": { "rol", "telefono" } }
    }
    """
    serializer_class = TierSystemTokenSerializer


# ---------------------------------------------------------------------------
# /api/auth/me/  — Datos del usuario autenticado
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    GET /api/auth/me/
    Header: Authorization: Bearer <access_token>
    Devuelve los datos completos del usuario autenticado.
    """
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# /api/auth/registro/  — Registro público (crea Agricultor)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def registro_view(request):
    """
    POST /api/auth/registro/
    Body: { "username", "email", "first_name", "last_name", "password", "password2", "telefono"(opcional) }
    Crea el usuario con rol AGRICULTOR y devuelve tokens listos para usar.
    """
    serializer = RegistroSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()

    # Emitir tokens directamente para que Flutter haga login automático tras el registro
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


# ---------------------------------------------------------------------------
# /api/auth/logout/  — Invalida el refresh token del cliente
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    POST /api/auth/logout/
    Body: { "refresh": "<refresh_token>" }
    Marca el refresh token como usado (el access expira solo).
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({"error": "Se requiere el refresh token."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RefreshToken(refresh_token)
        # Blacklist no está activado, pero la buena práctica es que Flutter borre el token localmente.
        # Si en el futuro se activa djangorestframework-simplejwt[blacklist], descomentar:
        # token.blacklist()
        return Response({"mensaje": "Sesión cerrada correctamente."})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
