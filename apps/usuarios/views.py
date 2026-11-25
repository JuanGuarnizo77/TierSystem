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
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse

from core.utils import (
    registrar_evento_seguridad,
    verificar_rate_limit,
    limpiar_rate_limit,
)
from .forms import RegistroForm


def login_view(request):
    """
    Vista de autenticación web tradicional (formulario HTML + sesión por cookies).

    Comportamiento:
      - Si el usuario ya cuenta con sesión activa, redirige a su panel correspondiente.
      - Al recibir POST, aplica control anti-fuerza bruta por IP y valida credenciales
        contra el backend de autenticación de Django.
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
        username_attempt = (request.POST.get('username') or '').strip().lower()[:60]

        try:
            from apps.ia_recomendaciones.models import ConfiguracionGlobal
            cfg_seg = ConfiguracionGlobal.load()
            limite_login = int(getattr(cfg_seg, 'max_intentos_login', 8) or 8)
            ventana_seg = int(getattr(cfg_seg, 'tiempo_bloqueo_min', 5) or 5) * 60
        except Exception:
            limite_login = 8
            ventana_seg = 300

        # Protección contra ataques de fuerza bruta tanto por IP como por cuenta de usuario (SRS)
        bloqueado_ip, _ = verificar_rate_limit(request, 'web_login', limite=limite_login, ventana_segundos=ventana_seg)
        bloqueado_usr = False
        if username_attempt:
            from django.core.cache import cache
            usr_key = f"rl:web_login_user:{username_attempt}"
            intentos_usr = cache.get(usr_key, 0)
            if intentos_usr >= limite_login:
                bloqueado_usr = True
            else:
                cache.set(usr_key, intentos_usr + 1, timeout=ventana_seg)

        if bloqueado_ip or bloqueado_usr:
            registrar_evento_seguridad(
                request, 'LOGIN_BLOQUEADO_FUERZA_BRUTA',
                f"Intento bloqueado por rate-limit para usuario='{username_attempt}'",
                nivel='WARNING',
            )
            form.add_error(
                None,
                'Demasiados intentos fallidos de inicio de sesión. Por seguridad, espere unos minutos antes de volver a intentarlo.'
            )
            return render(request, 'usuarios/login.html', {'form': form}, status=429)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # Verificación de credenciales con el subsistema auth de Django
            user = authenticate(username=username, password=password)
            if user is not None:
                limpiar_rate_limit(request, 'web_login')
                if username_attempt:
                    from django.core.cache import cache
                    cache.delete(f"rl:web_login_user:{username_attempt}")
                login(request, user)

                rol = user.perfil.rol if hasattr(user, 'perfil') else None
                registrar_evento_seguridad(
                    request, 'LOGIN_EXITOSO',
                    f"Inicio de sesión web exitoso (rol={rol})"
                )

                # Redirección dinámica según el rol operativo del usuario
                if rol == 'ADMIN':
                    return redirect('dashboard_admin')
                elif rol == 'LABORATORISTA':
                    return redirect('dashboard_laboratorista')
                else:
                    return redirect('dashboard_agricultor')
        else:
            registrar_evento_seguridad(
                request, 'LOGIN_FALLIDO',
                f"Credenciales inválidas para usuario='{request.POST.get('username', '')[:60]}'",
                nivel='WARNING',
            )
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
        bloqueado, _ = verificar_rate_limit(request, 'web_register', limite=10, ventana_segundos=600)
        if bloqueado:
            form = RegistroForm(request.POST)
            form.add_error(None, 'Demasiadas solicitudes de registro desde esta dirección. Intente más tarde.')
            return render(request, 'usuarios/register.html', {'form': form}, status=429)

        form = RegistroForm(request.POST)
        if form.is_valid():
            # Construye la entidad User sin persistir inmediatamente
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # El signal post_save garantiza la existencia del perfil; fijamos el rol y teléfono
            user.perfil.rol = 'AGRICULTOR'
            telefono_reg = (form.cleaned_data.get('telefono') or request.POST.get('telefono') or '').strip()[:20]
            if telefono_reg:
                user.perfil.telefono = telefono_reg
            user.perfil.save()

            # Inicio de sesión automático tras completar el registro
            login(request, user)
            registrar_evento_seguridad(
                request, 'REGISTRO_USUARIO',
                f"Nuevo agricultor registrado vía web: username='{user.username}'"
            )
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
            nombre = request.POST.get('first_name', '').strip()[:150]
            apellido = request.POST.get('last_name', '').strip()[:150]
            email = request.POST.get('email', '').strip().lower()[:254]
            telefono = request.POST.get('telefono', '').strip()[:20]

            user = request.user

            # Comprobación de formato y de que ningún otro usuario posea el mismo correo electrónico
            if email:
                try:
                    validate_email(email)
                except ValidationError:
                    return JsonResponse({'error': 'El formato del correo electrónico no es válido.'}, status=400)
                if User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
                    return JsonResponse({'error': 'El correo electrónico ya está registrado por otro usuario.'}, status=400)
                user.email = email

            user.first_name = nombre
            user.last_name = apellido
            user.save()

            # Actualización del número telefónico en el modelo de perfil
            if hasattr(user, 'perfil'):
                user.perfil.telefono = telefono
                user.perfil.save()

            registrar_evento_seguridad(request, 'PERFIL_ACTUALIZADO', 'Actualización de datos de perfil web')
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
                try:
                    validate_password(new_pass, user=user)
                except ValidationError as ve:
                    return JsonResponse({'error': ' '.join(ve.messages)}, status=400)

                user.set_password(new_pass)
                user.save()
                # Crucial: actualiza el hash en la sesión activa para evitar desautenticación inmediata
                update_session_auth_hash(request, user)
                registrar_evento_seguridad(request, 'CAMBIO_PASSWORD', 'Cambio de contraseña exitoso vía web')
                return JsonResponse({'mensaje': 'Contraseña actualizada con éxito.'})
            else:
                registrar_evento_seguridad(
                    request, 'CAMBIO_PASSWORD_FALLIDO',
                    'Contraseña actual incorrecta durante intento de cambio web', nivel='WARNING'
                )
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
