from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import RegistroAnalisis

@login_required(login_url='login')
def historial_analisis(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return redirect('home')
        
    analisis = RegistroAnalisis.objects.filter(solicitud__laboratorista_asignado=request.user).order_by('-fecha_analisis')
    return render(request, 'laboratorista/historial.html', {'analisis': analisis})
