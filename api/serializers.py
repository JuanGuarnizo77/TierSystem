from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.usuarios.models import Perfil


# ---------------------------------------------------------------------------
# Auth Serializers
# ---------------------------------------------------------------------------

class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ['rol', 'telefono']


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer de solo lectura para devolver los datos del usuario autenticado."""
    perfil = PerfilSerializer(read_only=True)
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'nombre_completo', 'perfil']

    def get_nombre_completo(self, obj):
        nombre = f"{obj.first_name} {obj.last_name}".strip()
        return nombre if nombre else obj.username


class RegistroSerializer(serializers.ModelSerializer):
    """
    Serializer para el registro público (siempre crea rol AGRICULTOR).
    Valida que las contraseñas coincidan y que el username/email no existan.
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirmar contraseña")
    telefono = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2', 'telefono']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ese nombre de usuario ya está en uso.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        telefono = validated_data.pop('telefono', '')
        validated_data.pop('password2')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )

        # El signal ya creó el Perfil; solo actualizamos el teléfono (rol = AGRICULTOR por defecto)
        if telefono:
            user.perfil.telefono = telefono
            user.perfil.save()

        return user
