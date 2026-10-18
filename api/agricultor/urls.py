from django.urls import path
from rest_framework.routers import DefaultRouter

from .views_terrenos import TerrenoViewSet
from .views_solicitudes import SolicitudViewSet
from .views_perfil import perfil_view, cambiar_password_view
from .views_resultados import historial_view, resultado_view, comparar_view
from .views_cultivos import catalogo_cultivos_view

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
] + router.urls