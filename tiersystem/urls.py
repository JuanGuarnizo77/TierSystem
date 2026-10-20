from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def api_root(request):
    return JsonResponse({
        "message": "TierSystem API Root",
        "version": "1.0",
        "endpoints": {
            "auth": "/api/v1/auth/",
        }
    })

urlpatterns = [
    path('superadmin/', admin.site.urls),
    # Redirigir /admin normal al panel del administrador
    path('admin/', lambda r: redirect('dashboard_admin')),
    # API v1 (móvil)
    path('api/v1/', include('api.urls')),
    # Rutas API legacy (web / sensor)
    path('api/', api_root, name='api-root'),
    path('', include('apps.usuarios.urls')),
    path('api/', include('apps.sensores.urls')),
    path('api/ia/', include('apps.ia_recomendaciones.urls')),
    path('laboratorista/solicitudes/', include('apps.solicitudes.urls')),
    path('laboratorista/analisis/', include('apps.analisis.urls')),
    # Rutas Agricultor
    path('agricultor/fincas/', include('apps.terrenos.urls')),
    path('agricultor/solicitudes/', include('apps.solicitudes.urls_agricultor')),
    path('agricultor/sipsa/', include('apps.sipsa.urls')),
    path('mercado/', include('apps.mercado.urls')),
    # Vista principal (PWA)
    path('', include('core.urls')),
]

# Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
