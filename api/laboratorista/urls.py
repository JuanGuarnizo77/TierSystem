from django.urls import path

from .views_dashboard import dashboard_view

urlpatterns = [
    path('dashboard/', dashboard_view, name='laboratorista_dashboard'),
]