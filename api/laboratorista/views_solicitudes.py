"""
Controlador de Gestión de Órdenes de Servicio - Perfil Laboratorista API.
Permite consultar el banco general de órdenes de estudio de suelos,
aceptar visitas programadas de manera concurrente segura (evitando condiciones de carrera),
rechazar solicitudes no viables y notificar al productor por correo SMTP.
"""

from datetime import date

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsLaboratorista
from apps.solicitudes.models import SolicitudAnalisis


def _solicitud_dict(s):
    """
    Serializa una entidad SolicitudAnalisis a un diccionario JSON enriquecido.
    Incluye datos del predio, hectáreas, cultivo de interés y etiquetas legibles.
    """
    return {
        'id': s.id,
        'agricultor': s.agricultor.get_full_name() or s.agricultor.username,
        'terreno': {
            'id': s.terreno_id,
            'nombre': s.terreno.nombre,
            'ubicacion': s.terreno.ubicacion,
            'hectareas': float(s.terreno.hectareas),
            'cultivo_principal': s.terreno.cultivo_principal,
        },
        'cultivo_deseado': s.cultivo_deseado,
        'modalidad': s.modalidad,
        'modalidad_texto': s.get_modalidad_display(),
        'notas_agricultor': s.notas_agricultor,
        'estado': s.estado,
        'estado_texto': s.get_estado_display(),
        'fecha_solicitud': s.fecha_solicitud,
        'fecha_visita': s.fecha_visita,
    }


def _base_qs():
    """
    Retorna el QuerySet base optimizado con select_related() para
    precargar en una sola consulta SQL las relaciones de agricultor y terreno.
    """
    return SolicitudAnalisis.objects.select_related('agricultor', 'terreno')


def _notificar(solicitud, laboratorista, estado, fecha_visita=None):
    """
    Despacha una notificación transaccional por correo electrónico SMTP al agricultor.
    Utiliza fail_silently=True y bloques try/except para garantizar que una caída
    temporal del servidor de correo no interrumpa la respuesta de la API móvil.
    """
    agricultor = solicitud.agricultor
    if not agricultor.email:
        return
    try:
        context = {
            'nombre_agricultor': agricultor.get_full_name() or agricultor.username,
            'nombre_finca': solicitud.terreno.nombre,
            'estado': estado,
            'nombre_laboratorista': laboratorista.get_full_name() or laboratorista.username,
        }
        if fecha_visita:
            context['fecha_visita'] = fecha_visita

        # Renderizado de plantilla HTML oficial
        html_message = render_to_string('emails/notificacion_solicitud.html', context)
        asunto = (
            'Tu solicitud ha sido ACEPTADA - TierSystem'
            if estado == 'ASIGNADA'
            else 'Actualización de tu solicitud - TierSystem'
        )
        send_mail(
            subject=asunto,
            message=strip_tags(html_message),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[agricultor.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        # Registro en consola para trazabilidad técnica sin afectar el flujo del usuario
        print(f"Error enviando correo de notificación: {e}")


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def pendientes_view(request):
    """
    GET /api/v1/laboratorista/solicitudes/pendientes/
    Lista todas las órdenes radicadas por agricultores que se encuentran libres en estado PENDIENTE.
    """
    qs = _base_qs().filter(estado='PENDIENTE').order_by('-fecha_solicitud')
    return Response([_solicitud_dict(s) for s in qs])


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def mis_tareas_view(request):
    """
    GET /api/v1/laboratorista/solicitudes/mis-tareas/
    Lista las órdenes activas (ASIGNADA o EN_PROCESO) bajo la responsabilidad del técnico en sesión.
    """
    qs = _base_qs().filter(
        laboratorista_asignado=request.user,
        estado__in=['ASIGNADA', 'EN_PROCESO'],
    ).order_by('-fecha_solicitud')
    return Response([_solicitud_dict(s) for s in qs])


@api_view(['POST'])
@permission_classes([IsLaboratorista])
def aceptar_view(request, solicitud_id):
    """
    POST /api/v1/laboratorista/solicitudes/<solicitud_id>/aceptar/
    Body JSON: {"fecha_visita": "YYYY-MM-DD"}
    Asigna la orden al técnico, fija la fecha de la visita técnica de muestreo
    y despacha la notificación SMTP al campesino.
    Usa UPDATE atómico en SQL para prevenir condiciones de carrera (Race Conditions).
    """
    texto = str(request.data.get('fecha_visita', '')).strip()
    if not texto:
        return Response({'error': 'La fecha de visita es obligatoria.'}, status=400)
    try:
        fecha = date.fromisoformat(texto)
    except ValueError:
        return Response({'error': 'Fecha inválida. Usa el formato AAAA-MM-DD.'}, status=400)

    # Actualización atómica en base de datos: si otro técnico la aceptó concurrentemente, retorna 0 filas afectadas
    actualizadas = SolicitudAnalisis.objects.filter(
        pk=solicitud_id, estado='PENDIENTE'
    ).update(
        laboratorista_asignado=request.user,
        estado='ASIGNADA',
        fecha_visita=fecha,
    )
    if not actualizadas:
        return Response(
            {'error': 'La solicitud ya no está pendiente o fue asignada previamente.'}, status=404
        )

    # Recupera la solicitud actualizada y dispara el correo de confirmación
    solicitud = get_object_or_404(_base_qs(), pk=solicitud_id)
    _notificar(solicitud, request.user, 'ASIGNADA', fecha_visita=texto)
    return Response({
        'mensaje': 'Solicitud aceptada y asignada correctamente.',
        'solicitud': _solicitud_dict(solicitud),
    })


@api_view(['POST'])
@permission_classes([IsLaboratorista])
def rechazar_view(request, solicitud_id):
    """
    POST /api/v1/laboratorista/solicitudes/<solicitud_id>/rechazar/
    Marca la orden en estado 'RECHAZADA' si no es viable operativamente y notifica al usuario.
    """
    actualizadas = SolicitudAnalisis.objects.filter(
        pk=solicitud_id, estado='PENDIENTE'
    ).update(estado='RECHAZADA')
    if not actualizadas:
        return Response(
            {'error': 'La solicitud ya no está pendiente.'}, status=404
        )

    solicitud = get_object_or_404(_base_qs(), pk=solicitud_id)
    _notificar(solicitud, request.user, 'RECHAZADA')
    return Response({'mensaje': 'Solicitud rechazada.'})


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def banco_view(request):
    """
    GET /api/v1/laboratorista/solicitudes/banco/
    Retorna la totalidad del flujo de solicitudes operativas organizadas con contadores por estado
    (PENDIENTE, ASIGNADA, EN_PROCESO, COMPLETADA) para visualización en pestañas móviles.
    """
    estados = ['PENDIENTE', 'ASIGNADA', 'EN_PROCESO', 'COMPLETADA']
    qs = _base_qs().filter(estado__in=estados).order_by('-fecha_solicitud')
    solicitudes = [_solicitud_dict(s) for s in qs]

    # Conteo agrupado por estado para renderizar insignias (badges) en la app Flutter
    conteos = {e: 0 for e in estados}
    for s in solicitudes:
        conteos[s['estado']] += 1

    return Response({'conteos': conteos, 'solicitudes': solicitudes})