from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Rutas de Recuperación de Contraseña
    path('recuperar-password/', auth_views.PasswordResetView.as_view(
        template_name='usuarios/password_reset_form.html',
        email_template_name='usuarios/password_reset_email.html',
        subject_template_name='usuarios/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done')
    ), name='password_reset'),
    
    path('recuperar-password/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='usuarios/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('recuperar-password/confirmar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='usuarios/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    ), name='password_reset_confirm'),
    
    path('recuperar-password/completado/', auth_views.PasswordResetCompleteView.as_view(
        template_name='usuarios/password_reset_complete.html'
    ), name='password_reset_complete'),
]

