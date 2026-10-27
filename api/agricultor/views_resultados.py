"""
Módulo de Vistas de Resultados y Comparativa Agronómica para Agricultores.
==========================================================================
Proporciona los controladores de API REST para la consulta de resultados
finales de análisis de suelo, historial de muestreos completados y la
herramienta de comparación edáfica diferencial entre dos análisis (US-0010).

Los análisis se cruzan dinámicamente con los requerimientos óptimos del cultivo
objetivo mediante el motor de evaluación agronómica, generando porcentajes
de compatibilidad, alertas de desbalance nutricional y cultivos alternativos.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.solicitudes.models import SolicitudAnalisis
from apps.solicitudes.views import _evaluar_parametros_agronomicos
from api.permissions import IsAgricultor


def _resumen(s, ev):
    """
    Construye una estructura de diccionario resumida para tarjetas de interfaz móvil.

    Parámetros:
        s (SolicitudAnalisis): Instancia del modelo de solicitud analizada.
        ev (dict): Diccionario retornado por `_evaluar_parametros_agronomicos`
                   con scores, niveles de compatibilidad y paletas de color.

    Retorna:
        dict: Metadatos clave y estado de compatibilidad optimizados para listas y tarjetas.
    """
    return {
        'id': s.id,
        'terreno_nombre': s.terreno.nombre,
        'cultivo': s.cultivo_deseado,
        'modalidad_texto': s.get_modalidad_display(),
        'fecha': s.fecha_solicitud.isoformat(),
        'compatibilidad': ev['compatibilidad'],
        'nivel': ev['nivel_compatibilidad'],
        'color': ev['color_compatibilidad'],
    }


def _completadas(user):
    """
    Consulta optimizada del conjunto de solicitudes completadas pertenecientes al agricultor.

    Aplica `select_related` sobre 'analisis_resultado' y 'terreno' para evitar el problema
    de consultas N+1 al iterar sobre los resultados en listas o comparativas.

    Parámetros:
        user (User): Usuario agricultor autenticado en la petición.

    Retorna:
        QuerySet: Solicitudes en estado 'COMPLETADA' ordenadas cronológicamente de forma descendente.
    """
    return (SolicitudAnalisis.objects
            .filter(agricultor=user, estado='COMPLETADA')
            .select_related('analisis_resultado', 'terreno')
            .order_by('-fecha_solicitud'))


@api_view(['GET'])
@permission_classes([IsAgricultor])
def historial_view(request):
    """
    GET /api/v1/agricultor/historial/
    ---------------------------------
    Recupera el listado consolidado de todos los análisis completados del agricultor autenticado.

    Flujo de ejecución:
      1. Recupera las solicitudes completadas del usuario mediante `_completadas()`.
      2. Itera sobre cada solicitud comprobando la existencia de `analisis_resultado`.
      3. Ejecuta la evaluación agronómica dinámica frente al cultivo deseado.
      4. Serializa la respuesta como una lista de tarjetas de resumen con scores de compatibilidad.
    """
    lista = []
    # Itera sobre el queryset precargado en memoria
    for s in _completadas(request.user):
        # Valida que el OneToOneField hacia RegistroAnalisis esté presente
        if hasattr(s, 'analisis_resultado'):
            ev = _evaluar_parametros_agronomicos(s.analisis_resultado, s.cultivo_deseado)
            lista.append(_resumen(s, ev))
    return Response(lista)


@api_view(['GET'])
@permission_classes([IsAgricultor])
def resultado_view(request, solicitud_id):
    """
    GET /api/v1/agricultor/resultados/<id>/
    ---------------------------------------
    Entrega el informe técnico detallado de un análisis completado.

    Garantiza aislamiento multi-inquilino validando que la solicitud pertenezca
    estrictamente al agricultor autenticado (`agricultor=request.user`).

    Contenido del reporte:
      - Datos del laboratorista asignado.
      - Mediciones físicas y químicas (pH, N, P, K, Humedad, Temperatura, CE).
      - Rango ideal vs medido y estado cualitativo (Bajo, Óptimo, Alto).
      - Recomendaciones agronómicas específicas de enmienda o fertilización.
      - Cultivos alternativos viables según el perfil edáfico del lote.
    """
    # Verificación de pertenencia y existencia; retorna 404 si no pertenece al agricultor
    s = get_object_or_404(SolicitudAnalisis, id=solicitud_id, agricultor=request.user)

    # Si la solicitud no ha culminado la fase de laboratorio, se rechaza la consulta
    if not hasattr(s, 'analisis_resultado'):
        return Response({'error': 'Esta solicitud aún no tiene análisis.'}, status=404)

    # Evaluación agronómica determinista basada en rangos edáficos de referencia
    ev = _evaluar_parametros_agronomicos(s.analisis_resultado, s.cultivo_deseado)
    data = _resumen(s, ev)

    # Inyección de detalles técnicos completos para la vista de detalle
    data.update({
        'laboratorista': (s.laboratorista_asignado.get_full_name() or s.laboratorista_asignado.username)
        if s.laboratorista_asignado else None,
        'fecha_analisis': s.analisis_resultado.fecha_analisis.isoformat(),
        'parametros': ev['parametros'],
        'recomendaciones': ev['recomendaciones'],
        'cultivos_alternativos': ev['cultivos_alternativos'],
        'consejo_general': ev['consejo_general'],
    })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAgricultor])
def comparar_view(request):
    """
    GET /api/v1/agricultor/comparar/?id1=..&id2=..
    ---------------------------------------------
    Herramienta de análisis edáfico comparativo entre dos solicitudes completadas.

    Permite al productor evaluar la evolución nutricional de un mismo terreno a lo largo
    del tiempo o contrastar las condiciones de dos lotes agrícolas distintos.

    Comportamiento:
      - Si no se especifican `id1` o `id2` por querystring, selecciona automáticamente
        los dos análisis completados más recientes.
      - Valida que el agricultor cuente con al menos dos análisis finalizados.
      - Realiza el match parámetro por parámetro (pH, N, P, K, etc.) calculando la
        diferencia aritmética directa (`val1 - val2`) y el diferencial de compatibilidad global.
    """
    # Filtrado en memoria de solicitudes que cuenten efectivamente con análisis registrado
    disponibles = [s for s in _completadas(request.user) if hasattr(s, 'analisis_resultado')]
    if len(disponibles) < 2:
        return Response({'error': 'Necesitas al menos 2 análisis completados para comparar.'}, status=400)

    # Resolución de identificadores: explícitos o los dos más recientes por defecto
    id1 = request.query_params.get('id1') or disponibles[0].id
    id2 = request.query_params.get('id2') or disponibles[1].id

    # Validación de seguridad multi-tenant para ambos registros
    s1 = get_object_or_404(SolicitudAnalisis, id=id1, agricultor=request.user)
    s2 = get_object_or_404(SolicitudAnalisis, id=id2, agricultor=request.user)

    if not hasattr(s1, 'analisis_resultado') or not hasattr(s2, 'analisis_resultado'):
        return Response({'error': 'Una solicitud no tiene análisis completado.'}, status=400)

    # Procesamiento agronómico de ambas muestras
    ev1 = _evaluar_parametros_agronomicos(s1.analisis_resultado, s1.cultivo_deseado)
    ev2 = _evaluar_parametros_agronomicos(s2.analisis_resultado, s2.cultivo_deseado)

    # Construcción de la matriz diferencial parámetro por parámetro
    filas = []
    for p1 in ev1['parametros']:
        # Búsqueda del parámetro equivalente en el segundo análisis
        p2 = next((p for p in ev2['parametros'] if p['nombre'] == p1['nombre']), None)
        if p2:
            filas.append({
                'parametro': p1['nombre'],
                'unidad': p1['unidad'],
                'ideal': p1['ideal'],
                'val1': p1['medido'],
                'estado1': p1['estado'],
                'val2': p2['medido'],
                'estado2': p2['estado'],
                'diferencia': round(p1['medido'] - p2['medido'], 2),
            })

    return Response({
        'disponibles': [_resumen(s, _evaluar_parametros_agronomicos(s.analisis_resultado, s.cultivo_deseado))
                        for s in disponibles],
        'a': _resumen(s1, ev1),
        'b': _resumen(s2, ev2),
        'diferencia_compatibilidad': ev1['compatibilidad'] - ev2['compatibilidad'],
        'filas': filas,
    })