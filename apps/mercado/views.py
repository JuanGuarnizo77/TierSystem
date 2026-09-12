from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import ProductoMercado

@login_required(login_url='login')
def mi_tienda(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')
        
    productos = ProductoMercado.objects.filter(vendedor=request.user).order_by('-fecha_publicacion')
    return render(request, 'agricultor/mi_tienda.html', {'productos': productos})

@login_required(login_url='login')
def agregar_producto(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        precio = request.POST.get('precio')
        cantidad = request.POST.get('cantidad')
        unidad = request.POST.get('unidad', 'kg')
        
        if not (nombre and precio and cantidad):
            return JsonResponse({'error': 'Faltan datos obligatorios'}, status=400)
            
        ProductoMercado.objects.create(
            vendedor=request.user,
            nombre=nombre,
            precio=precio,
            cantidad_disponible=cantidad,
            unidad_medida=unidad
        )
        return JsonResponse({'mensaje': 'Producto publicado en el mercado.'})
        
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def eliminar_producto(request, producto_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    if request.method == 'POST':
        try:
            prod = ProductoMercado.objects.get(id=producto_id, vendedor=request.user)
            prod.delete()
            return JsonResponse({'mensaje': 'Producto eliminado del mercado.'})
        except ProductoMercado.DoesNotExist:
            return JsonResponse({'error': 'El producto no existe.'}, status=404)
            
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required(login_url='login')
def mercado_publico(request):
    # Todos pueden ver el mercado, incluso laboratoristas si quisieran
    productos = ProductoMercado.objects.filter(activo=True).order_by('-fecha_publicacion')
    return render(request, 'agricultor/mercado.html', {'productos': productos})
