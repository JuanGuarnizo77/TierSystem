"""
Controladores Web de Gestión de Terrenos y Fincas Agrícolas.
============================================================
Proporciona la interfaz y los endpoints asíncronos (AJAX) para la administración
de predios agrícolas por parte del productor:
  - Listado de parcelas del agricultor (`mis_terrenos`).
  - Creación de nuevos lotes con coordenadas geográficas (`crear_terreno`).
  - Modificación de linderos, superficie y cultivo asignado (`editar_terreno`).
  - Eliminación segura de fincas con validación estricta de propiedad (`eliminar_terreno`).
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Terreno


@login_required(login_url='login')
def mis_terrenos(request):
    """
    Vista de panel principal de fincas del agricultor.

    Verificaciones:
      - Exige sesión autenticada con rol 'AGRICULTOR'.
      - Filtra exclusivamente los terrenos pertenecientes al usuario activo.

    Renderiza:
      - `agricultor/terrenos.html` con la lista de lotes ordenada por fecha de registro descendente.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    terrenos = Terreno.objects.filter(agricultor=request.user).order_by('-fecha_registro')
    return render(request, 'agricultor/terrenos.html', {'terrenos': terrenos})


@login_required(login_url='login')
def crear_terreno(request):
    """
    Endpoint AJAX para el registro de un nuevo lote o finca agrícola.

    Parámetros POST:
      - `nombre` (str): Nombre identificador del predio.
      - `ubicacion` (str): Municipio, vereda o corregimiento.
      - `hectareas` (float): Superficie en hectáreas.
      - `cultivo` (str|int): Identificador o nombre del cultivo principal.
      - `coordenadas_poligono` (str): GeoJSON perimetral obtenido desde Leaflet.

    Validaciones:
      - Autorización por rol 'AGRICULTOR'.
      - Presencia obligatoria de nombre, ubicación y extensión territorial.
      - Parseo numérico seguro del tamaño en hectáreas.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        ubicacion = request.POST.get('ubicacion')
        hectareas = request.POST.get('hectareas')
        cultivo_principal = request.POST.get('cultivo')
        coordenadas_poligono = request.POST.get('coordenadas_poligono')

        # Comprobación de campos obligatorios
        if not (nombre and ubicacion and hectareas):
            return JsonResponse({'error': 'Faltan datos obligatorios'}, status=400)

        # Conversión y validación numérica
        try:
            hectareas = float(hectareas)
        except ValueError:
            return JsonResponse({'error': 'El tamaño debe ser un número válido'}, status=400)

        # Instanciación asignando automáticamente al agricultor de la sesión
        t = Terreno(
            agricultor=request.user,
            nombre=nombre,
            ubicacion=ubicacion,
            hectareas=hectareas,
            coordenadas_poligono=coordenadas_poligono
        )
        # El setter polimórfico resuelve la clave foránea a Cultivo
        t.cultivo_principal = cultivo_principal
        t.save()
        return JsonResponse({'mensaje': 'Finca registrada correctamente.'})

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url='login')
def eliminar_terreno(request, terreno_id):
    """
    Endpoint AJAX para la baja física de una finca agrícola.

    Seguridad Multi-Inquilino:
      - La cláusula de búsqueda incluye `agricultor=request.user`, imposibilitando
        que un usuario elimine fincas de terceros alterando el identificador en la petición.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            # Recuperación atómica vinculada al propietario
            terreno = Terreno.objects.get(id=terreno_id, agricultor=request.user)
            terreno.delete()
            return JsonResponse({'mensaje': 'Finca eliminada.'})
        except Terreno.DoesNotExist:
            return JsonResponse({'error': 'La finca no existe.'}, status=404)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url='login')
def editar_terreno(request, terreno_id):
    """
    Endpoint AJAX para la modificación de los atributos de una finca existente.

    Garantiza aislamiento de datos al requerir coincidencia estricta de propiedad
    y aplica validaciones numéricas sobre el área en hectáreas antes de persistir.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        try:
            # Aislamiento multi-tenant por clave primaria y agricultor autenticado
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

            # Actualización de atributos validados
            terreno.nombre = nombre
            terreno.ubicacion = ubicacion
            terreno.hectareas = hectareas

            if cultivo_principal is not None:
                terreno.cultivo_principal = cultivo_principal
            if coordenadas_poligono is not None:
                terreno.coordenadas_poligono = coordenadas_poligono

            terreno.save()
            return JsonResponse({'mensaje': 'Finca actualizada correctamente.'})
        except Terreno.DoesNotExist:
            return JsonResponse({'error': 'La finca no existe.'}, status=404)

    return JsonResponse({'error': 'Método no permitido'}, status=405)
