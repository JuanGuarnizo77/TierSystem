from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, me_view, registro_view, logout_view

urlpatterns = [
    path('login/',    LoginView.as_view(),        name='api_login'),
    path('refresh/',  TokenRefreshView.as_view(), name='api_token_refresh'),
    path('me/',       me_view,                    name='api_me'),
    path('registro/', registro_view,              name='api_registro'),
    path('logout/',   logout_view,                name='api_logout'),
]
