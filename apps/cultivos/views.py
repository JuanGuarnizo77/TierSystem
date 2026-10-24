from django.http import JsonResponse
from django.shortcuts import render
from .models import Cultivo

def api_catalogo_offline(request):
    """
    Retorna el catálogo completo de cultivos con rangos óptimos y pisos altitudinales.
    Utilizado por el Service Worker y la PWA para pre-cargar la base de datos local
    en IndexedDB y operar 100% offline en zonas rurales sin internet.
    """
    cultivos = Cultivo.objects.filter(activo=True).order_by('nombre')
    data = [c.to_dict() for c in cultivos]
    return JsonResponse({
        "estado": "ok",
        "total": len(data),
        "cultivos": data
    })
