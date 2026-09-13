from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('agricultor/dashboard/', views.dashboard_agricultor, name='dashboard_agricultor'),
    path('agricultor/cultivos/', views.catalogo_cultivos, name='catalogo_cultivos'),
    path('laboratorista/dashboard/', views.dashboard_laboratorista, name='dashboard_laboratorista'),
    
    # Rutas Administrador
    path('administrador/dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('administrador/usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('administrador/laboratoristas/nuevo/', views.crear_laboratorista, name='crear_laboratorista'),
    path('administrador/usuarios/<int:user_id>/estado/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('administrador/usuarios/<int:user_id>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
    
    # Supervisión y Reportes
    path('administrador/supervision/', views.supervision_analisis, name='supervision_analisis'),
    path('administrador/supervision/exportar-pdf/', views.exportar_pdf, name='exportar_pdf'),
    path('administrador/supervision/exportar-excel/', views.exportar_excel, name='exportar_excel'),
    # Configuración de Cultivos
    path('administrador/cultivos/', views.gestion_cultivos_admin, name='gestion_cultivos_admin'),
    path('administrador/cultivos/guardar/', views.guardar_cultivo_admin, name='guardar_cultivo_admin'),
    path('administrador/cultivos/<int:cultivo_id>/eliminar/', views.eliminar_cultivo_admin, name='eliminar_cultivo_admin'),
]
