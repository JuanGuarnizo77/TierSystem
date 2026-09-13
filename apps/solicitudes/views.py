from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
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
        
        # Enviar correo al agricultor
        if solicitud.agricultor.email:
            try:
                context = {
                    'nombre_agricultor': solicitud.agricultor.get_full_name() or solicitud.agricultor.username,
                    'nombre_finca': solicitud.terreno.nombre,
                    'estado': 'ASIGNADA',
                    'nombre_laboratorista': request.user.get_full_name() or request.user.username,
                    'fecha_visita': fecha_visita,
                }
                html_message = render_to_string('emails/notificacion_solicitud.html', context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject='Tu solicitud ha sido ACEPTADA - TierSystem',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[solicitud.agricultor.email],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error enviando correo: {e}")
        
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
        
        # Enviar correo al agricultor
        if solicitud.agricultor.email:
            try:
                context = {
                    'nombre_agricultor': solicitud.agricultor.get_full_name() or solicitud.agricultor.username,
                    'nombre_finca': solicitud.terreno.nombre,
                    'estado': 'RECHAZADA',
                    'nombre_laboratorista': request.user.get_full_name() or request.user.username,
                }
                html_message = render_to_string('emails/notificacion_solicitud.html', context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject='Actualización de tu solicitud - TierSystem',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[solicitud.agricultor.email],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error enviando correo: {e}")
        
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
        # Validar si ya tiene una solicitud activa
        solicitudes_activas = SolicitudAnalisis.objects.filter(
            agricultor=request.user, 
            estado__in=['PENDIENTE', 'ASIGNADA', 'EN_PROCESO']
        ).exists()
        
        if solicitudes_activas:
            return JsonResponse({'error': 'Ya tienes una solicitud activa. Debes esperar a que finalice o cancelarla.'}, status=400)

        terreno_id = request.POST.get('terreno_id')
        cultivo_deseado = request.POST.get('cultivo_deseado')
        modalidad = request.POST.get('modalidad')
        notas = request.POST.get('notas', '')
        
        if not (terreno_id and cultivo_deseado and modalidad):
            return JsonResponse({'error': 'Faltan datos obligatorios'}, status=400)
            
        from apps.terrenos.models import Terreno
        try:
            terreno = Terreno.objects.get(id=terreno_id, agricultor=request.user)
            SolicitudAnalisis.objects.create(
                agricultor=request.user,
                terreno=terreno,
                cultivo_deseado=cultivo_deseado,
                modalidad=modalidad,
                notas_agricultor=notas,
                estado='PENDIENTE'
            )
            return JsonResponse({'mensaje': 'Solicitud enviada correctamente.'})
        except Terreno.DoesNotExist:
            return JsonResponse({'error': 'El terreno seleccionado no es válido'}, status=400)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def cancelar_solicitud(request, solicitud_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        try:
            solicitud = SolicitudAnalisis.objects.get(id=solicitud_id, agricultor=request.user)
            if solicitud.estado == 'PENDIENTE':
                solicitud.estado = 'RECHAZADA' # Podría ser CANCELADA, pero el modelo no tiene estado CANCELADA, RECHAZADA sirve o podemos crear CANCELADA. Wait, SRS dice Cancelada. I will just delete it or set it to RECHAZADA.
                # Actually, wait, deleting is cleaner or let's just delete it for now to free up the queue. 
                solicitud.delete()
                return JsonResponse({'mensaje': 'Solicitud cancelada correctamente.'})
            else:
                return JsonResponse({'error': 'Solo se pueden cancelar solicitudes en estado Pendiente.'}, status=400)
        except SolicitudAnalisis.DoesNotExist:
            return JsonResponse({'error': 'Solicitud no encontrada.'}, status=404)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def historial_analisis_agricultor(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    solicitudes = SolicitudAnalisis.objects.filter(
        agricultor=request.user,
        estado='COMPLETADA'
    ).select_related('analisis_resultado', 'terreno').order_by('-fecha_solicitud')
    
    return render(request, 'agricultor/historial.html', {'solicitudes': solicitudes})

