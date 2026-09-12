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
                    return redirect('/admin/') # Al panel nativo de django o propio
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
