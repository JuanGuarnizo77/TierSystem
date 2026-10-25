"""
Controladores de Catálogo Agrícola para Sincronización Local.
============================================================
Proporciona endpoints HTTP para la entrega de catálogos agronómicos orientados
a la operación sin conexión (Offline-First) en la aplicación web progresiva (PWA).

Permite que el Service Worker almacene en caché las fichas agronómicas y alimente
el almacén local de Dexie.js (IndexedDB) para que los laboratoristas de campo
puedan evaluar cultivos y tomar lecturas en zonas rurales sin cobertura móvil.
"""

from django.http import JsonResponse
from django.shortcuts import render
from .models import Cultivo


def api_catalogo_offline(request):
    """
    Endpoint HTTP: GET /cultivos/api/catalogo-offline/
    --------------------------------------------------
    Genera el paquete completo de cultivos activos con sus rangos edáficos óptimos.

    Este payload JSON es consumido durante el evento de instalación y sincronización
    periódica del Service Worker (`static/js/service-worker.js`), poblando la tabla
    `cultivos` en Dexie.js (`static/js/db.js`).

    Respuestas:
      - 200 OK: Objeto JSON con el conteo total y el arreglo de cultivos serializados
                con sus rangos numéricos de pH, humedad, temperatura, CE y nutrientes.
    """
    # Consulta de cultivos activos ordenados alfabéticamente
    cultivos = Cultivo.objects.filter(activo=True).order_by('nombre')

    # Transformación a diccionarios de tipos nativos (float e int)
    data = [c.to_dict() for c in cultivos]

    return JsonResponse({
        "estado": "ok",
        "total": len(data),
        "cultivos": data
    })
