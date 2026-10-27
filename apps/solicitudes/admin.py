"""
Configuración del Panel Administrativo de Django para Solicitudes.
==================================================================
Registra el modelo `SolicitudAnalisis` en la interfaz administrativa central,
permitiendo la auditoría del ciclo de atención, técnicos asignados y estados.
"""

from django.contrib import admin
from .models import SolicitudAnalisis


@admin.register(SolicitudAnalisis)
class SolicitudAnalisisAdmin(admin.ModelAdmin):
    """Panel de administración y control del flujo de solicitudes de análisis."""
    list_display = (
        'id',
        'agricultor',
        'terreno',
        'estado',
        'modalidad',
        'cultivo_deseado_ref',
        'laboratorista_asignado',
        'fecha_solicitud',
        'fecha_visita',
    )
    list_filter = ('estado', 'modalidad', 'fecha_solicitud')
    search_fields = (
        'agricultor__username',
        'agricultor__email',
        'terreno__nombre',
        'cultivo_deseado_ref__nombre',
    )
    ordering = ('-fecha_solicitud',)
