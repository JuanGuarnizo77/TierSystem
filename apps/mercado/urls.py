from django.urls import path
from . import views

app_name = 'mercado'

urlpatterns = [
    path('', views.precios_sipsa, name='precios_sipsa'),
]
