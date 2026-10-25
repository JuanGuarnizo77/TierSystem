"""
Enrutador de Endpoints para el Perfil Agricultor - TierSystem Mobile API.
Define los servicios REST consumidos por la aplicación Flutter para productores:
1. ViewSets de CRUD: Terrenos/Fincas y Órdenes de Solicitud de Análisis.
2. Perfil de usuario y actualización de credenciales.
3. Historial de análisis edafológicos, visualización de informes y comparativa de lotes.
4. Consulta del catálogo oficial de cultivos de Huila.
5. Seguimiento a cotizaciones mayoristas SIPSA/DANE y aliados comerciales.
6. Reportes especializados de tendencias de mercado.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views_terrenos import TerrenoViewSet
from .views_solicitudes import SolicitudViewSet
from .views_perfil import perfil_view, cambiar_password_view
from .views_resultados import historial_view, resultado_view, comparar_view
from .views_cultivos import catalogo_cultivos_view
from .views_mercado import precios_sipsa_view, actualizar_precios_view
from .views_reportes import reportes_lista_view, reportes_detalle_view

# Enrutador automático de ViewSets para endpoints REST estándar (list, retrieve, create, update, destroy)
router = DefaultRouter()
router.register(r'terrenos', TerrenoViewSet, basename='agricultor_terrenos')
router.register(r'solicitudes', SolicitudViewSet, basename='agricultor_solicitudes')

urlpatterns = [
    # Consulta y edición del perfil del productor (teléfono, datos básicos)
    path('perfil/', perfil_view, name='agricultor_perfil'),
    # Modificación de contraseña con verificación de clave previa
    path('perfil/password/', cambiar_password_view, name='agricultor_perfil_password'),

    # Historial de estudios de suelo solicitados por el agricultor
    path('historial/', historial_view, name='agricultor_historial'),
    # Detalle de un análisis finalizado con recomendaciones de fertilización
    path('resultados/<int:solicitud_id>/', resultado_view, name='agricultor_resultado'),
    # Comparativa fisicoquímica entre dos o más lotes de la finca
    path('comparar/', comparar_view, name='agricultor_comparar'),

    # Catálogo taxonómico y edafológico de cultivos del Huila
    path('cultivos/', catalogo_cultivos_view, name='agricultor_cultivos'),

    # Cotizaciones mayoristas del DANE y proyección de tendencias
    path('mercado/precios/', precios_sipsa_view, name='agricultor_mercado_precios'),
    # Disparador para refrescar cotizaciones recientes
    path('mercado/actualizar/', actualizar_precios_view, name='agricultor_mercado_actualizar'),

    # Módulo de reportes y análisis de mercado por cultivo
    path('reportes/', reportes_lista_view, name='agricultor_reportes'),
    path('reportes/<int:cultivo_id>/', reportes_detalle_view, name='agricultor_reportes_detalle'),
] + router.urls