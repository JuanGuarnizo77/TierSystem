from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views_auth import LoginView, me_view, registro_view, logout_view

urlpatterns = [
    # Auth
    path('auth/login/',    LoginView.as_view(),  name='api_login'),
    path('auth/refresh/',  TokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/me/',       me_view,              name='api_me'),
    path('auth/registro/', registro_view,        name='api_registro'),
    path('auth/logout/',   logout_view,          name='api_logout'),
]
