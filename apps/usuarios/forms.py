"""
Formularios de Registro y Validación de Cuentas de Usuario.
==========================================================
Define los formularios web basados en modelos (`ModelForm`) para el registro
de nuevos usuarios en la plataforma TierSystem, integrando validación cruzada
de credenciales y estilos preconfigurados para Tailwind CSS.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class RegistroForm(forms.ModelForm):
    """
    Formulario de autoservicio para el registro inicial de productores agrícolas.

    Gestiona la captura de credenciales (`username`, `email`) y el par de contraseñas
    con verificación de doble entrada antes de delegar la persistencia a la vista.
    """

    # Campo de captura de teléfono celular o de contacto (SRS)
    telefono = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all',
            'placeholder': 'Ej: 3101234567'
        }),
        label="Teléfono de Contacto"
    )

    # Campo de captura para la contraseña con máscara de entrada
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all',
            'placeholder': 'Tu contraseña'
        }),
        label="Contraseña"
    )

    # Campo de confirmación para evitar errores tipográficos del usuario
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all',
            'placeholder': 'Confirma tu contraseña'
        }),
        label="Confirmar Contraseña"
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all',
                'placeholder': 'Nombre de usuario'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all',
                'placeholder': 'ejemplo@correo.com'
            })
        }

    def clean_email(self):
        """Valida que el correo electrónico sea obligatorio y único en el sistema."""
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError("El correo electrónico es obligatorio.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean(self):
        """
        Validación cruzada a nivel de formulario.

        Comprueba que la clave de confirmación coincida exactamente con la
        contraseña principal introducida por el usuario y aplica los validadores
        de fortaleza de contraseña de Django (`AUTH_PASSWORD_VALIDATORS`).

        Lanza:
            forms.ValidationError: Si los valores difieren o no cumplen la política de seguridad.
        """
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        if password:
            validate_password(password)
        return cleaned_data
