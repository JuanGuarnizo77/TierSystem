from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import SolicitudAnalisis

@login_required(login_url='login')
def solicitudes_pendientes(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return redirect('home')
        
    solicitudes = SolicitudAnalisis.objects.filter(estado='PENDIENTE').order_by('-fecha_solicitud')
    return render(request, 'laboratorista/solicitudes_pendientes.html', {'solicitudes': solicitudes})

@login_required(login_url='login')
def solicitudes_asignadas(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return redirect('home')
        
    solicitudes = SolicitudAnalisis.objects.filter(laboratorista_asignado=request.user, estado__in=['ASIGNADA', 'EN_PROCESO']).order_by('-fecha_solicitud')
    return render(request, 'laboratorista/mis_solicitudes.html', {'solicitudes': solicitudes})

@login_required(login_url='login')
def aceptar_solicitud(request, solicitud_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAnalisis, id=solicitud_id, estado='PENDIENTE')
        fecha_visita = request.POST.get('fecha_visita')
        
        if not fecha_visita:
            return JsonResponse({'error': 'La fecha de visita es obligatoria'}, status=400)
            
        solicitud.laboratorista_asignado = request.user
        solicitud.estado = 'ASIGNADA'
        solicitud.fecha_visita = fecha_visita
        solicitud.save()
        
        return JsonResponse({'mensaje': 'Solicitud aceptada y asignada correctamente.'})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def rechazar_solicitud(request, solicitud_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAnalisis, id=solicitud_id, estado='PENDIENTE')
        solicitud.estado = 'RECHAZADA'
        solicitud.save()
        
        return JsonResponse({'mensaje': 'Solicitud rechazada.'})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def mis_solicitudes_agricultor(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    solicitudes = SolicitudAnalisis.objects.filter(agricultor=request.user).order_by('-fecha_solicitud')
    # Necesitamos pasar los terrenos para el select al crear
    from apps.terrenos.models import Terreno
    terrenos = Terreno.objects.filter(agricultor=request.user)
    
    return render(request, 'agricultor/solicitudes.html', {'solicitudes': solicitudes, 'terrenos': terrenos})

@login_required(login_url='login')
def crear_solicitud(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        terreno_id = request.POST.get('terreno_id')
        notas = request.POST.get('notas', '')
        
        from apps.terrenos.models import Terreno
        try:
            terreno = Terreno.objects.get(id=terreno_id, agricultor=request.user)
            SolicitudAnalisis.objects.create(
                agricultor=request.user,
                terreno=terreno,
                notas_agricultor=notas,
                estado='PENDIENTE'
            )
            return JsonResponse({'mensaje': 'Solicitud enviada correctamente.'})
        except Terreno.DoesNotExist:
            return JsonResponse({'error': 'El terreno seleccionado no es válido'}, status=400)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

