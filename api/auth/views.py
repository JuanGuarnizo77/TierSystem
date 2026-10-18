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
    POST /api/v1/auth/login/
    Body: { "username": "...", "password": "..." }
    """
    serializer_class = TierSystemTokenSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    GET /api/v1/auth/me/
    Header: Authorization: Bearer <access_token>
    """
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def registro_view(request):
    """
    POST /api/v1/auth/registro/
    Body: { "username", "email", "first_name", "last_name", "password", "password2", "telefono"(opcional) }
    """
    serializer = RegistroSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()

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
    POST /api/v1/auth/logout/
    Body: { "refresh": "<refresh_token>" }
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({"error": "Se requiere el refresh token."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        RefreshToken(refresh_token)
        return Response({"mensaje": "Sesión cerrada correctamente."})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
