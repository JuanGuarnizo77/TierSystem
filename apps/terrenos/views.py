from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Terreno

@login_required(login_url='login')
def mis_terrenos(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    terrenos = Terreno.objects.filter(agricultor=request.user).order_by('-fecha_registro')
    return render(request, 'agricultor/terrenos.html', {'terrenos': terrenos})

@login_required(login_url='login')
def crear_terreno(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        ubicacion = request.POST.get('ubicacion')
        hectareas = request.POST.get('hectareas')
        cultivo_principal = request.POST.get('cultivo')
        coordenadas_poligono = request.POST.get('coordenadas_poligono')
        
        if not (nombre and ubicacion and hectareas):
            return JsonResponse({'error': 'Faltan datos obligatorios'}, status=400)
            
        try:
            hectareas = float(hectareas)
        except ValueError:
            return JsonResponse({'error': 'El tamaño debe ser un número válido'}, status=400)
            
        Terreno.objects.create(
            agricultor=request.user,
            nombre=nombre,
            ubicacion=ubicacion,
            hectareas=hectareas,
            cultivo_principal=cultivo_principal,
            coordenadas_poligono=coordenadas_poligono
        )
        return JsonResponse({'mensaje': 'Finca registrada correctamente.'})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def eliminar_terreno(request, terreno_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        try:
            terreno = Terreno.objects.get(id=terreno_id, agricultor=request.user)
            terreno.delete()
            return JsonResponse({'mensaje': 'Finca eliminada.'})
        except Terreno.DoesNotExist:
            return JsonResponse({'error': 'La finca no existe.'}, status=404)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def editar_terreno(request, terreno_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        try:
            terreno = Terreno.objects.get(id=terreno_id, agricultor=request.user)
            nombre = request.POST.get('nombre')
            ubicacion = request.POST.get('ubicacion')
            hectareas = request.POST.get('hectareas')
            cultivo_principal = request.POST.get('cultivo')
            coordenadas_poligono = request.POST.get('coordenadas_poligono')
            
            if not (nombre and ubicacion and hectareas):
                return JsonResponse({'error': 'Faltan datos obligatorios'}, status=400)
                
            try:
                hectareas = float(hectareas)
            except ValueError:
                return JsonResponse({'error': 'El tamaño debe ser un número válido'}, status=400)
                
            terreno.nombre = nombre
            terreno.ubicacion = ubicacion
            terreno.hectareas = hectareas
            if cultivo_principal is not None: # check if passed (even empty)
                terreno.cultivo_principal = cultivo_principal
            if coordenadas_poligono is not None:
                terreno.coordenadas_poligono = coordenadas_poligono
            terreno.save()
            return JsonResponse({'mensaje': 'Finca actualizada correctamente.'})
        except Terreno.DoesNotExist:
            return JsonResponse({'error': 'La finca no existe.'}, status=404)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)
