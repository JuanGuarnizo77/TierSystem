"""
Enrutamiento URL Central y Paneles Administrativos de TierSystem.
=================================================================
Define la topología de rutas para:
  1. Vistas públicas y aterrizaje institucional (`home`).
  2. Paneles de control principales de cada rol (`dashboard_agricultor`, `dashboard_laboratorista`, `dashboard_admin`).
  3. Módulo de campo para laboratoristas (`toma_muestras_laboratorista`).
  4. Panel de administración y gobernanza:
      - Gestión de usuarios y creación de laboratoristas.
      - Supervisión técnica de análisis y exportaciones ejecutivas (PDF/Excel).
      - Catálogo de cultivos y calibración edafológica.
      - Diagnóstico de hardware (telemetría de sensores IoT).
      - Configuración global del sistema (umbrales y timeouts de IA).
"""

from django.urls import path
from . import views

urlpatterns = [
    # Ruta de aterrizaje institucional (landing page pública)
    path('', views.home, name='home'),

    # Rutas para el rol Agricultor
    path('agricultor/dashboard/', views.dashboard_agricultor, name='dashboard_agricultor'),
    path('agricultor/cultivos/', views.catalogo_cultivos, name='catalogo_cultivos'),

    # Rutas para el rol Laboratorista
    path('laboratorista/dashboard/', views.dashboard_laboratorista, name='dashboard_laboratorista'),
    path('laboratorista/toma-muestras/', views.toma_muestras_laboratorista, name='toma_muestras_laboratorista'),

    # =========================================================================
    # Rutas del Panel de Administración (Supervisión, Usuarios y Auditoría)
    # =========================================================================
    path('administrador/dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('administrador/usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('administrador/laboratoristas/nuevo/', views.crear_laboratorista, name='crear_laboratorista'),
    path('administrador/usuarios/<int:user_id>/editar/', views.editar_usuario, name='editar_usuario'),
    path('administrador/usuarios/<int:user_id>/estado/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('administrador/usuarios/<int:user_id>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),

    # Supervisión Global y Exportación Ejecutiva de Análisis
    path('administrador/supervision/', views.supervision_analisis, name='supervision_analisis'),
    path('administrador/supervision/exportar-pdf/', views.exportar_pdf, name='exportar_pdf'),
    path('administrador/supervision/exportar-excel/', views.exportar_excel, name='exportar_excel'),

    # Mantenimiento del Catálogo de Especies Agrícolas
    path('administrador/cultivos/', views.gestion_cultivos_admin, name='gestion_cultivos_admin'),
    path('administrador/cultivos/guardar/', views.guardar_cultivo_admin, name='guardar_cultivo_admin'),
    path('administrador/cultivos/<int:cultivo_id>/eliminar/', views.eliminar_cultivo_admin, name='eliminar_cultivo_admin'),

    # Diagnóstico de Hardware y Telemetría de Sensores en Campo
    path('administrador/hardware/', views.estado_hardware, name='estado_hardware'),

    # Configuración Global del Ecosistema (Gobernanza de IA y Rangos Físicos)
    path('administrador/configuracion/', views.configuracion_global_view, name='configuracion_global'),
]
