"""
Controladores Web de Autenticación, Registro y Perfil de Usuario.
=================================================================
Gestiona el ciclo de vida de sesiones web basadas en cookies de Django:
  1. Inicio de sesión (`login_view`) con redirección dinámica por rol.
  2. Registro de autoservicio para agricultores (`register_view`).
  3. Actualización asíncrona (AJAX/Fetch) de datos personales y cambio de clave
     con preservación de sesión activa (`perfil_view`).
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse

from .forms import RegistroForm


def login_view(request):
    """
    Vista de autenticación web tradicional (formulario HTML + sesión por cookies).

    Comportamiento:
      - Si el usuario ya cuenta con sesión activa, redirige a su panel correspondiente.
      - Al recibir POST, valida credenciales contra el backend de autenticación de Django.
      - Tras autenticar exitosamente, inspecciona el rol en `user.perfil.rol` y redirige a:
          * 'ADMIN' -> `dashboard_admin`
          * 'LABORATORISTA' -> `dashboard_laboratorista`
          * 'AGRICULTOR' -> `dashboard_agricultor`
    """
    # Si la sesión ya está iniciada, se evita presentar el formulario de login
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # Verificación de credenciales con el subsistema auth de Django
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)

                # Redirección dinámica según el rol operativo del usuario
                rol = user.perfil.rol if hasattr(user, 'perfil') else None
                if rol == 'ADMIN':
                    return redirect('dashboard_admin')
                elif rol == 'LABORATORISTA':
                    return redirect('dashboard_laboratorista')
                else:
                    return redirect('dashboard_agricultor')
    else:
        form = AuthenticationForm()

    return render(request, 'usuarios/login.html', {'form': form})


def register_view(request):
    """
    Vista de autoregistro público para nuevos productores agrícolas.

    Flujo operativo:
      1. Procesa y valida el formulario `RegistroForm`.
      2. Crea el objeto `User` aplicando hashing criptográfico a la contraseña.
      3. Asegura la asignación explícita del rol 'AGRICULTOR' en la entidad `Perfil`.
      4. Inicia la sesión automáticamente tras el registro (`login()`).
      5. Redirige al productor a su panel principal (`dashboard_agricultor`).
    """
    if request.user.is_authenticated:
        return redirect('dashboard_agricultor')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            # Construye la entidad User sin persistir inmediatamente
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # El signal post_save garantiza la existencia del perfil; fijamos el rol
            user.perfil.rol = 'AGRICULTOR'
            user.perfil.save()

            # Inicio de sesión automático tras completar el registro
            login(request, user)
            return redirect('dashboard_agricultor')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/register.html', {'form': form})


@login_required(login_url='login')
def perfil_view(request):
    """
    Controlador unificado de visualización y edición del perfil del usuario.

    Soporta operaciones asíncronas vía AJAX/Fetch mediante el campo `action`:
      - `update_info`: Modifica nombres, correo y teléfono, validando unicidad de email.
      - `change_password`: Valida la contraseña previa, aplica la nueva con PBKDF2 y
        ejecuta `update_session_auth_hash` para evitar que Django cierre la sesión.

    En peticiones GET, renderiza la plantilla HTML adaptada al rol del usuario autenticado:
      - 'ADMIN' -> 'admin/perfil.html'
      - 'LABORATORISTA' -> 'laboratorista/perfil.html'
      - 'AGRICULTOR' -> 'agricultor/perfil.html'
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        # ---------------------------------------------------------------------
        # Acción 1: Actualización de Información Personal
        # ---------------------------------------------------------------------
        if action == 'update_info':
            nombre = request.POST.get('first_name', '').strip()
            apellido = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()

            user = request.user

            # Comprobación de que ningún otro usuario posea el mismo correo electrónico
            if email:
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    return JsonResponse({'error': 'El correo electrónico ya está registrado por otro usuario.'}, status=400)
                user.email = email

            user.first_name = nombre
            user.last_name = apellido
            user.save()

            # Actualización del número telefónico en el modelo de perfil
            if hasattr(user, 'perfil'):
                user.perfil.telefono = telefono
                user.perfil.save()

            return JsonResponse({'mensaje': 'Perfil actualizado correctamente.'})

        # ---------------------------------------------------------------------
        # Acción 2: Cambio Seguro de Contraseña
        # ---------------------------------------------------------------------
        elif action == 'change_password':
            old_pass = request.POST.get('old_password')
            new_pass = request.POST.get('new_password')
            confirm_pass = request.POST.get('confirm_password')

            if not old_pass or not new_pass:
                return JsonResponse({'error': 'Debes indicar la contraseña actual y la nueva.'}, status=400)

            if confirm_pass and new_pass != confirm_pass:
                return JsonResponse({'error': 'Las contraseñas nuevas no coinciden.'}, status=400)

            if len(new_pass) < 6:
                return JsonResponse({'error': 'La nueva contraseña debe tener al menos 6 caracteres.'}, status=400)

            user = request.user
            # Valida la clave actual contra el hash almacenado
            if user.check_password(old_pass):
                user.set_password(new_pass)
                user.save()
                # Crucial: actualiza el hash en la sesión activa para evitar desautenticación inmediata
                update_session_auth_hash(request, user)
                return JsonResponse({'mensaje': 'Contraseña actualizada con éxito.'})
            else:
                return JsonResponse({'error': 'La contraseña actual es incorrecta.'}, status=400)

    # -------------------------------------------------------------------------
    # Renderizado GET: Selección de la plantilla visual según el rol activo
    # -------------------------------------------------------------------------
    rol = request.user.perfil.rol if hasattr(request.user, 'perfil') else None

    if rol == 'ADMIN':
        template = 'admin/perfil.html'
    elif rol == 'LABORATORISTA':
        template = 'laboratorista/perfil.html'
    else:
        template = 'agricultor/perfil.html'

    return render(request, template)
