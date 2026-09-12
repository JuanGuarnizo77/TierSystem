from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_view, name='registro'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
]
