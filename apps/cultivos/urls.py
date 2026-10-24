from django.urls import path
from . import views

app_name = 'cultivos'

urlpatterns = [
    path('api/catalogo-offline/', views.api_catalogo_offline, name='api_catalogo_offline'),
]
