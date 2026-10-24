from django.urls import path
from rest_framework.routers import DefaultRouter

from .views_terrenos import TerrenoViewSet
from .views_solicitudes import SolicitudViewSet
from .views_perfil import perfil_view, cambiar_password_view
from .views_resultados import historial_view, resultado_view, comparar_view
from .views_cultivos import catalogo_cultivos_view
from .views_mercado import precios_sipsa_view, actualizar_precios_view
from .views_reportes import reportes_lista_view, reportes_detalle_view

router = DefaultRouter()
router.register(r'terrenos', TerrenoViewSet, basename='agricultor_terrenos')
router.register(r'solicitudes', SolicitudViewSet, basename='agricultor_solicitudes')

urlpatterns = [
    path('perfil/', perfil_view, name='agricultor_perfil'),
    path('perfil/password/', cambiar_password_view, name='agricultor_perfil_password'),
    path('historial/', historial_view, name='agricultor_historial'),
    path('resultados/<int:solicitud_id>/', resultado_view, name='agricultor_resultado'),
    path('comparar/', comparar_view, name='agricultor_comparar'),
    path('cultivos/', catalogo_cultivos_view, name='agricultor_cultivos'),
    path('mercado/precios/', precios_sipsa_view, name='agricultor_mercado_precios'),
    path('mercado/actualizar/', actualizar_precios_view, name='agricultor_mercado_actualizar'),
    path('reportes/', reportes_lista_view, name='agricultor_reportes'),
    path('reportes/<int:cultivo_id>/', reportes_detalle_view, name='agricultor_reportes_detalle'),
] + router.urls