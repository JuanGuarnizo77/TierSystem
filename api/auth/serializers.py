"""
Serializadores del Módulo de Autenticación de la API REST - TierSystem.
Maneja la serialización del modelo User y Perfil, validación de contraseñas con PBKDF2,
reglas de unicidad de correo y creación segura de cuentas de agricultores.
"""

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.usuarios.models import Perfil


class PerfilSerializer(serializers.ModelSerializer):
    """
    Serializador anidado para exponer los atributos complementarios del perfil.
    Traduce el rol del sistema ('AGRICULTOR', 'LABORATORISTA', 'ADMIN') y el teléfono móvil.
    """
    class Meta:
        model = Perfil
        fields = ['rol', 'telefono']


class UsuarioSerializer(serializers.ModelSerializer):
    """
    Serializador de solo lectura para la información del usuario autenticado (/auth/me/).
    Combina atributos nativos de auth_user con datos del perfil y un método derivado para nombres completos.
    """
    # Anida el perfil relacional OneToOneField definido en apps.usuarios
    perfil = PerfilSerializer(read_only=True)
    # Atributo calculado dinámicamente para interfaces que requieran presentación limpia
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'nombre_completo', 'perfil']

    def get_nombre_completo(self, obj):
        """Retorna nombres y apellidos concatenados o el nombre de usuario como respaldo."""
        nombre = f"{obj.first_name} {obj.last_name}".strip()
        return nombre if nombre else obj.username


class RegistroSerializer(serializers.ModelSerializer):
    """
    Serializador de entrada para el registro público de nuevos productores en la app móvil.
    Aplica políticas estrictas de seguridad (contraseñas coincidentes y validadores de Django)
    y aprovisiona automáticamente el rol 'AGRICULTOR'.
    """
    # Campo de solo escritura que pasa por los validadores de complejidad de settings.py
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    # Campo de confirmación para evitar errores de mecanografía durante el registro
    password2 = serializers.CharField(write_only=True, required=True, label="Confirmar contraseña")
    # Teléfono de contacto opcional que se traslada al modelo Perfil
    telefono = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2', 'telefono']

    def validate_email(self, value):
        """Garantiza que el correo electrónico no esté registrado previamente en otra cuenta."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return value

    def validate_username(self, value):
        """Previene duplicados en el identificador único de usuario."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ese nombre de usuario ya está en uso.")
        return value

    def validate(self, attrs):
        """Comprobación cruzada para verificar igualdad exacta entre ambas contraseñas."""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        """
        Crea la entidad User en base de datos. La contraseña es encriptada automáticamente
        por create_user() mediante PBKDF2 con hash SHA-256.
        """
        # Extrae datos que no pertenecen a las columnas nativas de la tabla auth_user
        telefono = validated_data.pop('telefono', '')
        validated_data.pop('password2')

        # Persistencia en auth_user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )

        # La señal post_save en apps/usuarios/models.py crea automáticamente el Perfil;
        # procedemos a registrar el teléfono si fue proporcionado por el agricultor
        if telefono:
            user.perfil.telefono = telefono
            user.perfil.save()

        return user

