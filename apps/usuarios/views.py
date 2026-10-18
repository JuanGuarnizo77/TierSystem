from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegistroForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home') # Luego redirigirá a los paneles correspondientes

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Redirigir según rol
                rol = user.perfil.rol if hasattr(user, 'perfil') else None
                if rol == 'ADMIN':
                    return redirect('dashboard_admin') # Al panel personalizado
                elif rol == 'LABORATORISTA':
                    return redirect('dashboard_laboratorista') 
                else:
                    return redirect('dashboard_agricultor') 
    else:
        form = AuthenticationForm()
        
    return render(request, 'usuarios/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_agricultor')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            # El signal en models.py se encargará de crear el perfil.
            # Nos aseguramos de que el rol por defecto sea AGRICULTOR.
            user.perfil.rol = 'AGRICULTOR'
            user.perfil.save()
            
            # Loguear al usuario recién creado
            login(request, user)
            return redirect('dashboard_agricultor')
    else:
        form = RegistroForm()
        
    return render(request, 'usuarios/register.html', {'form': form})

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash

@login_required(login_url='login')
def perfil_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_info':
            nombre = request.POST.get('first_name', '').strip()
            apellido = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            
            user = request.user
            
            if email:
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    return JsonResponse({'error': 'El correo electrónico ya está registrado por otro usuario.'}, status=400)
                user.email = email
                
            user.first_name = nombre
            user.last_name = apellido
            user.save()
            
            if hasattr(user, 'perfil'):
                user.perfil.telefono = telefono
                user.perfil.save()
                
            return JsonResponse({'mensaje': 'Perfil actualizado correctamente.'})
            
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
            if user.check_password(old_pass):
                user.set_password(new_pass)
                user.save()
                update_session_auth_hash(request, user)  # Importante para que no cierre sesión
                return JsonResponse({'mensaje': 'Contraseña actualizada con éxito.'})
            else:
                return JsonResponse({'error': 'La contraseña actual es incorrecta.'}, status=400)
                
    # Determinamos la plantilla según el rol para mantener el diseño base correspondiente
    rol = request.user.perfil.rol if hasattr(request.user, 'perfil') else None
    
    if rol == 'ADMIN':
        template = 'admin/perfil.html'
    elif rol == 'LABORATORISTA':
        template = 'laboratorista/perfil.html'
    else:
        template = 'agricultor/perfil.html'
    
    return render(request, template)

