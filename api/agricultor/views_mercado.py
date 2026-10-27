"""
Módulo de Vistas de Mercado Agropecuario y Sincronización SIPSA para Agricultores.
==================================================================================
Gestiona las cotizaciones de mercado agropecuario para el departamento del Huila,
evaluando la frescura y disponibilidad de los datos respecto a los boletines
semanales del SIPSA/DANE.

Permite consultar el estado de conexión del servicio de precios y ejecutar
la sincronización bajo demanda mediante el comando de gestión `actualizar_sipsa`.
"""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAgricultor
from apps.sipsa.models import PrecioSemanal
from apps.mercado.views import (
    DATOS_MERCADO_HUILA,
    _normalizar_tendencia,
    _get_compradores_for_cultivo,
)


@api_view(['GET'])
@permission_classes([IsAgricultor])
def precios_sipsa_view(request):
    """
    GET /api/v1/agricultor/mercado/precios/
    ---------------------------------------
    Retorna la lista de precios de mercado agropecuario para los cultivos principales
    del Huila, acompañada del estado de actualización de la información.

    Diagnóstico de frescura temporal:
      - 'online': Información con menos de 24 horas de antigüedad.
      - 'reciente': Datos registrados entre 24 y 72 horas atrás.
      - 'desactualizado': Más de 72 horas sin ingesta de nuevos boletines oficiales.

    Estructura de cada cultivo:
      - Precios promedio nacional y regional Huila.
      - Tendencia de mercado ('Alza', 'Baja', 'Estable').
      - Variación porcentual inter-período.
      - Directorio de compradores y centros de acopio autorizados en la región.
    """
    ahora = timezone.now()

    # Inspección de la última fecha de sincronización registrada en la tabla de precios
    ps_reciente = PrecioSemanal.objects.order_by('-fecha_registro').first()
    ultima_global = None
    if ps_reciente and ps_reciente.fecha_registro:
        ts = ps_reciente.fecha_registro
        dias = (ahora - ts).days
        ultima_global = timezone.localtime(ts).strftime("%d/%m/%Y %H:%M")

        # Clasificación del estado de frescura de los datos según umbrales de tiempo
        if ts >= ahora - timedelta(hours=24):
            estado = 'online'
            mensaje = f"Precios actualizados al {ultima_global} desde SIPSA/DANE."
        elif ts >= ahora - timedelta(hours=72):
            estado = 'reciente'
            mensaje = f"Precios con {dias} día(s) de antigüedad. Se recomienda actualizar."
        else:
            estado = 'desactualizado'
            mensaje = f"Precios con más de 72h de antigüedad ({dias} días). Mostrando datos de referencia."
    else:
        estado = 'reciente'
        mensaje = "Mostrando precios oficiales y de referencia regional Huila."

    # Ensamblado de cotizaciones combinando datos de mercado con compradores locales
    nombres = list(DATOS_MERCADO_HUILA.keys())
    tabla = []
    for nombre in nombres:
        d = DATOS_MERCADO_HUILA.get(nombre, {})
        if d:
            tabla.append({
                'cultivo': nombre,
                'precio_promedio': d.get('precio_promedio', 0),
                'precio_local': d.get('precio_local', d.get('precio_promedio', 0)),
                'unidad': d.get('unidad', 'kg'),
                'tendencia': _normalizar_tendencia(d.get('tendencia', 'Estable')),
                'variacion_porcentaje': float(
                    str(d.get('variacion', '0%')).replace('%', '').replace('+', '')
                ),
                'fuente': d.get('fuente', 'SIPSA / DANE'),
                'ultima_actualizacion': '—',
                'dias_desde_actualizacion': None,
                'compradores': _get_compradores_for_cultivo(nombre),
                'historial': d.get('historial', []),
            })

    return Response({
        'estado_conexion': estado,
        'mensaje_conexion': mensaje,
        'ultima_actualizacion_global': ultima_global,
        'fecha_hoy': timezone.localtime(ahora).strftime("%d/%m/%Y"),
        'precios': tabla,
    })


@api_view(['POST'])
@permission_classes([IsAgricultor])
def actualizar_precios_view(request):
    """
    POST /api/v1/agricultor/mercado/actualizar/
    -------------------------------------------
    Ejecuta sincrónicamente el comando de gestión Django `actualizar_sipsa`.

    Descarga y parsea los boletines más recientes de SIPSA/DANE, actualizando
    los registros de `PrecioSemanal` y disparando el reentrenamiento del modelo
    predictivo de series temporales.

    Respuestas:
      - 200 OK: Proceso exitoso con captura del log de consola generado por el comando.
      - 500 Internal Server Error: Si ocurre una excepción de red o parsing.
    """
    out = StringIO()
    try:
        # Invocación programática del management command de Django redirigiendo stdout
        call_command('actualizar_sipsa', stdout=out)
        return Response({'status': 'ok', 'output': out.getvalue()})
    except Exception as exc:
        # Captura y notificación de errores durante la conexión o el parseo
        return Response({'status': 'error', 'error': str(exc)}, status=500)