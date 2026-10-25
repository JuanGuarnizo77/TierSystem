"""
Enrutamiento URL para Autenticación Web y Gestión de Cuentas.
============================================================
Define los patrones de URL para el inicio y cierre de sesión basado en sesiones,
autoregistro de productores, perfil de usuario y el flujo completo de recuperación
de contraseña por correo electrónico provisto por `django.contrib.auth.views`.
"""

from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Rutas principales de autenticación y cuenta de usuario
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # =========================================================================
    # Flujo Integral de Recuperación de Contraseña por Correo (Password Reset)
    # =========================================================================
    # 1. Formulario de solicitud inicial de reseteo (ingreso de correo)
    path(
        'recuperar-password/',
        auth_views.PasswordResetView.as_view(
            template_name='usuarios/password_reset_form.html',
            email_template_name='usuarios/password_reset_email.html',
            subject_template_name='usuarios/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done')
        ),
        name='password_reset'
    ),

    # 2. Confirmación de correo enviado con instrucciones
    path(
        'recuperar-password/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='usuarios/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    # 3. Enlace criptográfico de un solo uso con uid base64 y token temporal
    path(
        'recuperar-password/confirmar/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='usuarios/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete')
        ),
        name='password_reset_confirm'
    ),

    # 4. Notificación de cambio de contraseña exitoso
    path(
        'recuperar-password/completado/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='usuarios/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]
