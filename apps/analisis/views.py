"""
Controladores Web de Análisis de Suelo y Auditoría Técnica.
===========================================================
Gestiona la visualización del histórico de análisis procesados en laboratorio
por los técnicos de campo en la plataforma web de escritorio.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import RegistroAnalisis


@login_required(login_url='login')
def historial_analisis(request):
    """
    Vista de historial técnico de análisis de suelos para laboratoristas.

    Restricciones:
      - Requiere sesión autenticada con rol 'LABORATORISTA'.
      - Filtra exclusivamente las solicitudes donde el usuario actual fue el
        técnico responsable (`solicitud__laboratorista_asignado=request.user`).

    Renderiza:
      - `laboratorista/historial.html` con los análisis ordenados cronológicamente.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'LABORATORISTA':
        return redirect('home')

    # Consulta de los análisis ejecutados por el laboratorista autenticado
    analisis = RegistroAnalisis.objects.filter(
        solicitud__laboratorista_asignado=request.user
    ).order_by('-fecha_analisis')

    return render(request, 'laboratorista/historial.html', {'analisis': analisis})
