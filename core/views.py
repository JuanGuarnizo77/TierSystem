from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'perfil'):
            if request.user.perfil.rol == 'LABORATORISTA':
                return redirect('dashboard_laboratorista')
            elif request.user.perfil.rol == 'AGRICULTOR':
                return redirect('dashboard_agricultor')
    return render(request, 'home.html')

@login_required(login_url='login')
def dashboard_agricultor(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'AGRICULTOR':
        from apps.terrenos.models import Terreno
        from apps.solicitudes.models import SolicitudAnalisis
        from apps.mercado.models import ProductoMercado
        
        context = {
            'total_terrenos': Terreno.objects.filter(agricultor=request.user).count(),
            'solicitudes_activas': SolicitudAnalisis.objects.filter(agricultor=request.user).exclude(estado='COMPLETADA').count(),
            'total_productos': ProductoMercado.objects.filter(vendedor=request.user).count(),
        }
        return render(request, 'agricultor/dashboard.html', context)
    return redirect('home')

@login_required(login_url='login')
def catalogo_cultivos(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'AGRICULTOR':
        # Lista estática de cultivos para demostración (puede venir de DB luego)
        cultivos = [
            {'nombre': 'Café', 'clima': 'Templado', 'ph': '5.0 - 5.5', 'humedad': '60% - 80%', 'img': 'fa-mug-hot'},
            {'nombre': 'Maíz', 'clima': 'Cálido', 'ph': '5.8 - 7.0', 'humedad': '50% - 70%', 'img': 'fa-seedling'},
            {'nombre': 'Cacao', 'clima': 'Tropical', 'ph': '6.0 - 7.5', 'humedad': '70% - 90%', 'img': 'fa-leaf'},
            {'nombre': 'Frijol', 'clima': 'Templado', 'ph': '5.5 - 6.5', 'humedad': '50% - 60%', 'img': 'fa-plant-wilt'},
            {'nombre': 'Plátano', 'clima': 'Tropical', 'ph': '5.5 - 7.0', 'humedad': '75% - 85%', 'img': 'fa-tree'},
        ]
        return render(request, 'agricultor/cultivos.html', {'cultivos': cultivos})
    return redirect('home')

@login_required(login_url='login')
def dashboard_laboratorista(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'LABORATORISTA':
        from apps.solicitudes.models import SolicitudAnalisis
        from apps.analisis.models import RegistroAnalisis
        
        solicitud_id = request.GET.get('solicitud_id')
        context = {
            'total_pendientes': SolicitudAnalisis.objects.filter(estado='PENDIENTE').count(),
            'total_completados': RegistroAnalisis.objects.filter(solicitud__laboratorista_asignado=request.user).count(),
        }
        
        if solicitud_id:
            try:
                solicitud = SolicitudAnalisis.objects.get(id=solicitud_id, laboratorista_asignado=request.user)
                context['solicitud_activa'] = solicitud
            except SolicitudAnalisis.DoesNotExist:
                pass
                
        return render(request, 'laboratorista/dashboard.html', context)
    else:
        return redirect('home')

