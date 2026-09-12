from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({"message": "TierSystem API Root"})

urlpatterns = [
    path('admin/', admin.site.urls),
    # Rutas API
    path('api/', api_root, name='api-root'),
    path('', include('apps.usuarios.urls')),
    # path('api/terrenos/', include('apps.terrenos.urls')),
    # path('api/solicitudes/', include('apps.solicitudes.urls')),
    path('api/', include('apps.sensores.urls')),
    path('api/ia/', include('apps.ia_recomendaciones.urls')),
    path('laboratorista/solicitudes/', include('apps.solicitudes.urls')),
    path('laboratorista/analisis/', include('apps.analisis.urls')),
    
    # Rutas Agricultor
    path('agricultor/fincas/', include('apps.terrenos.urls')),
    path('agricultor/solicitudes/', include('apps.solicitudes.urls_agricultor')),
    path('mercado/', include('apps.mercado.urls')),
    
    # Vista principal (PWA)
    path('', include('core.urls')),
]
