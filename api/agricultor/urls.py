from django.urls import path
from rest_framework.routers import DefaultRouter

from .views_terrenos import TerrenoViewSet
from .views_solicitudes import SolicitudViewSet
from .views_perfil import perfil_view, cambiar_password_view

router = DefaultRouter()
router.register(r'terrenos', TerrenoViewSet, basename='agricultor_terrenos')
router.register(r'solicitudes', SolicitudViewSet, basename='agricultor_solicitudes')

urlpatterns = [
    path('perfil/', perfil_view, name='agricultor_perfil'),
    path('perfil/password/', cambiar_password_view, name='agricultor_perfil_password'),
] + router.urls