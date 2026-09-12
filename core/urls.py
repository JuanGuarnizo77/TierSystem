from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('agricultor/dashboard/', views.dashboard_agricultor, name='dashboard_agricultor'),
    path('agricultor/cultivos/', views.catalogo_cultivos, name='catalogo_cultivos'),
    path('laboratorista/dashboard/', views.dashboard_laboratorista, name='dashboard_laboratorista'),
]
