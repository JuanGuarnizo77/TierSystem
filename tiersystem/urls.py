"""
Enrutador Principal de URLs del Proyecto TierSystem.
=====================================================
Define la raíz de la topología de enrutamiento HTTP del ecosistema agrotecnológico:
  1. Panel Administrativo Django Superuser (`superadmin/`).
  2. Redirección de conveniencia (`admin/` -> `dashboard_admin`).
  3. API RESTful Móvil v1 (`api/v1/`) gestionada mediante Django REST Framework y JWT.
  4. Endpoints telemétricos y de sensores IoT (`api/`).
  5. Motor de inferencia agronómica por Inteligencia Artificial (`api/ia/`).
  6. Módulos de gestión por roles:
      - Laboratorista: órdenes de trabajo edafológico (`laboratorista/solicitudes/`)
        y procesamiento de muestras (`laboratorista/analisis/`).
      - Agricultor: predios/lotes (`agricultor/fincas/`), solicitudes de servicio (`agricultor/solicitudes/`)
        y sistema de precios de referencia mayoristas SIPSA/DANE (`agricultor/sipsa/`).
      - Transversales: mercado agrícola regional (`mercado/`), catálogo biológico (`cultivos/`)
        y autenticación/sesiones (`apps.usuarios.urls`).
  7. Enrutador central PWA y vistas base (`core.urls`).
  8. Configuración para el servicio de medios (`media/`) durante entornos de desarrollo (`DEBUG=True`).
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static


def api_root(request):
    """
    Vista de bienvenida e índice descriptivo de la API REST de TierSystem.

    Proporciona metadatos básicos de versión y puntos de entrada disponibles
    para clientes móviles, dispositivos IoT y servicios de integración externos.

    Parámetros:
      - `request` (HttpRequest): Solicitud HTTP entrante.

    Retorna:
      - `JsonResponse`: Objeto JSON con el estado de la API, versión y endpoints principales.
    """
    return JsonResponse({
        "message": "TierSystem API Root",
        "version": "1.0",
        "endpoints": {
            "auth": "/api/v1/auth/",
        }
    })


# Topología de rutas URL raíz del servidor Django
urlpatterns = [
    # Interfaz nativa de administración de Django (restringida a superusuarios)
    path('superadmin/', admin.site.urls),

    # Redirección amigable: envía el acceso estándar /admin/ al dashboard administrativo personalizado
    path('admin/', lambda r: redirect('dashboard_admin')),

    # API Móvil RESTful v1 (Autenticación JWT, Endpoints de sincronización offline y consultas)
    path('api/v1/', include('api.urls')),

    # Endpoint raíz de información sobre la API
    path('api/', api_root, name='api-root'),

    # Autenticación de usuarios, registro, restablecimiento de credenciales y sesiones web
    path('', include('apps.usuarios.urls')),

    # Telemetría de sensores IoT de campo (sonda de 7 parámetros fisicoquímicos)
    path('api/', include('apps.sensores.urls')),

    # Motor de recomendaciones agronómicas asistidas por IA (Google Gemini + motor local)
    path('api/ia/', include('apps.ia_recomendaciones.urls')),

    # Rutas operativas del Laboratorista: órdenes de servicio y cuadrículas de campo
    path('laboratorista/solicitudes/', include('apps.solicitudes.urls')),

    # Procesamiento técnico de muestras y cálculo de resultados edafológicos
    path('laboratorista/analisis/', include('apps.analisis.urls')),

    # Rutas operativas del Agricultor: cartografía de predios y fincas
    path('agricultor/fincas/', include('apps.terrenos.urls')),

    # Solicitudes de análisis de suelo radicadas por el productor
    path('agricultor/solicitudes/', include('apps.solicitudes.urls_agricultor')),

    # Monitor de precios agrícolas mayoristas del Huila y proyecciones SIPSA/DANE
    path('agricultor/sipsa/', include('apps.sipsa.urls')),

    # Directorio de compradores regionales, cooperativas y canales de comercialización directa
    path('mercado/', include('apps.mercado.urls')),

    # Catálogo taxonómico y agroclimático de especies y variedades aptas para el Huila
    path('cultivos/', include('apps.cultivos.urls')),

    # Núcleo de la plataforma: vistas principales, tableros de control y diseño PWA
    path('', include('core.urls')),
]

# Servir archivos estáticos subidos por usuarios (multimedia/firmas/certificados) en modo depuración
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
