"""
Módulo de Catálogo Agrícola para Productores.
=============================================
Proporciona el endpoint REST para la consulta del catálogo oficial de cultivos
adaptados a la geografía y agroclimatología del departamento del Huila.

Suministra información agronómica base (rangos ideales de pH, nitrógeno, fósforo,
potasio, humedad, temperatura y conductividad eléctrica) para consulta offline
y sincronización en el almacenamiento local del dispositivo móvil (Dexie.js / IndexedDB).
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsAgricultor
from apps.cultivos.models import Cultivo


@api_view(['GET'])
@permission_classes([IsAgricultor])
def catalogo_cultivos_view(request):
    """
    GET /api/v1/agricultor/cultivos/
    --------------------------------
    Retorna el listado completo de cultivos activos registrados en el sistema.

    Cada elemento incluye los umbrales agronómicos óptimos requeridos para el
    cálculo de compatibilidad edáfica y la toma de decisiones agrícolas.

    Respuestas:
      - 200 OK: Lista serializada de cultivos con sus parámetros fisicoquímicos ideales.
    """
    # Consulta los cultivos habilitados ordenados alfabéticamente
    cultivos = Cultivo.objects.filter(activo=True).order_by('nombre')

    # Serializa cada cultivo invocando el método to_catalogo_dict() definido en el modelo
    return Response([c.to_catalogo_dict() for c in cultivos])