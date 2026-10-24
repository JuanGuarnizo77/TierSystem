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
    return SolicitudAnalisis.objects.select_related('agricultor', 'terreno')


def _notificar(solicitud, laboratorista, estado, fecha_visita=None):
    """Envía correo al agricultor (igual que la web). Nunca rompe la API."""
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
        print(f"Error enviando correo: {e}")


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def pendientes_view(request):
    """GET /api/v1/laboratorista/solicitudes/pendientes/"""
    qs = _base_qs().filter(estado='PENDIENTE').order_by('-fecha_solicitud')
    return Response([_solicitud_dict(s) for s in qs])


@api_view(['GET'])
@permission_classes([IsLaboratorista])
def mis_tareas_view(request):
    """GET /api/v1/laboratorista/solicitudes/mis-tareas/"""
    qs = _base_qs().filter(
        laboratorista_asignado=request.user,
        estado__in=['ASIGNADA', 'EN_PROCESO'],
    ).order_by('-fecha_solicitud')
    return Response([_solicitud_dict(s) for s in qs])


@api_view(['POST'])
@permission_classes([IsLaboratorista])
def aceptar_view(request, solicitud_id):
    """
    POST /api/v1/laboratorista/solicitudes/<id>/aceptar/
    Body: {"fecha_visita": "YYYY-MM-DD"}
    """
    texto = str(request.data.get('fecha_visita', '')).strip()
    if not texto:
        return Response({'error': 'La fecha de visita es obligatoria.'}, status=400)
    try:
        fecha = date.fromisoformat(texto)
    except ValueError:
        return Response({'error': 'Fecha inválida. Usa el formato AAAA-MM-DD.'}, status=400)

    # Actualización atómica: si otro laboratorista la tomó antes, no se cambia nada.
    actualizadas = SolicitudAnalisis.objects.filter(
        pk=solicitud_id, estado='PENDIENTE'
    ).update(
        laboratorista_asignado=request.user,
        estado='ASIGNADA',
        fecha_visita=fecha,
    )
    if not actualizadas:
        return Response(
            {'error': 'La solicitud ya no está pendiente.'}, status=404
        )

    solicitud = get_object_or_404(_base_qs(), pk=solicitud_id)
    _notificar(solicitud, request.user, 'ASIGNADA', fecha_visita=texto)
    return Response({
        'mensaje': 'Solicitud aceptada y asignada correctamente.',
        'solicitud': _solicitud_dict(solicitud),
    })


@api_view(['POST'])
@permission_classes([IsLaboratorista])
def rechazar_view(request, solicitud_id):
    """POST /api/v1/laboratorista/solicitudes/<id>/rechazar/"""
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