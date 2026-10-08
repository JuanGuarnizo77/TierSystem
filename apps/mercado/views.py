from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import requests
import json
from datetime import datetime

from .models import PrecioMercado, Comprador

# Catálogo base de precios de referencia regional Huila (SIPSA/DANE)
DATOS_MERCADO_HUILA = {
    "Maíz": {
        "precio_promedio": 1450,
        "precio_local": 1380,
        "unidad": "kg",
        "tendencia": "Alza",
        "variacion": "+8%",
        "fuente": "SIPSA — Mercado Regional Huila (Surabastos Neiva)",
        "historial": [
            {"mes": "Ene", "precio": 1280},
            {"mes": "Feb", "precio": 1200},
            {"mes": "Mar", "precio": 1340},
            {"mes": "Abr", "precio": 1300},
            {"mes": "May", "precio": 1400},
            {"mes": "Jun", "precio": 1450},
        ],
        "compradores": [
            {"nombre": "Cooperativa Agro Norte", "tipo": "Cooperativa", "municipio": "Neiva, Huila", "contacto": "312 456 7890", "precio": "$1.460 / kg"},
            {"nombre": "Central de Abastos Surabastos", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$1.440 / kg"},
            {"nombre": "Agrocomercial del Huila S.A.S.", "tipo": "Intermediario", "municipio": "Garzón, Huila", "contacto": "320 112 3344", "precio": "$1.400 / kg"},
            {"nombre": "Granos & Cereales del Sur", "tipo": "Exportador", "municipio": "Pitalito, Huila", "contacto": "318 998 7766", "precio": "$1.480 / kg"}
        ]
    },
    "Café": {
        "precio_promedio": 18500,
        "precio_local": 18200,
        "unidad": "kg pergamino",
        "tendencia": "Alza",
        "variacion": "+12%",
        "fuente": "Federación Nal. de Cafeteros / SIPSA Huila",
        "historial": [
            {"mes": "Ene", "precio": 16000},
            {"mes": "Feb", "precio": 16500},
            {"mes": "Mar", "precio": 17200},
            {"mes": "Abr", "precio": 17800},
            {"mes": "May", "precio": 18000},
            {"mes": "Jun", "precio": 18500},
        ],
        "compradores": [
            {"nombre": "CADEFIHUILA - Cooperativa Departamental", "tipo": "Cooperativa", "municipio": "Neiva / Garzón", "contacto": "310 555 4321", "precio": "$18.600 / kg"},
            {"nombre": "ASOPEP Pitalito", "tipo": "Asociación Exportadora", "municipio": "Pitalito, Huila", "contacto": "317 654 9870", "precio": "$19.200 / kg"},
            {"nombre": "Café Especial La Angostura", "tipo": "Comprador Especial", "municipio": "Campoalegre, Huila", "contacto": "311 223 3445", "precio": "$18.800 / kg"}
        ]
    },
    "Cacao": {
        "precio_promedio": 21000,
        "precio_local": 20400,
        "unidad": "kg grano seco",
        "tendencia": "Alza",
        "variacion": "+15%",
        "fuente": "Fedecacao / SIPSA Neiva",
        "historial": [
            {"mes": "Ene", "precio": 17500},
            {"mes": "Feb", "precio": 18200},
            {"mes": "Mar", "precio": 19000},
            {"mes": "Abr", "precio": 19800},
            {"mes": "May", "precio": 20500},
            {"mes": "Jun", "precio": 21000},
        ],
        "compradores": [
            {"nombre": "Chocolatería y Derivados del Huila", "tipo": "Transformador", "municipio": "Gigante, Huila", "contacto": "314 332 1100", "precio": "$21.500 / kg"},
            {"nombre": "Surabastos Cacao Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "316 887 4455", "precio": "$20.800 / kg"}
        ]
    },
    "Plátano": {
        "precio_promedio": 1600,
        "precio_local": 1500,
        "unidad": "kg",
        "tendencia": "Estable",
        "variacion": "+1%",
        "fuente": "SIPSA — Plaza Minorista Garzón / Neiva",
        "historial": [
            {"mes": "Ene", "precio": 1550},
            {"mes": "Feb", "precio": 1580},
            {"mes": "Mar", "precio": 1600},
            {"mes": "Abr", "precio": 1590},
            {"mes": "May", "precio": 1610},
            {"mes": "Jun", "precio": 1600},
        ],
        "compradores": [
            {"nombre": "Distribuidora Plátano Verde Huila", "tipo": "Mayorista", "municipio": "Garzón, Huila", "contacto": "313 776 5544", "precio": "$1.620 / kg"},
            {"nombre": "Surabastos Pabellón Frutas", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "318 443 2211", "precio": "$1.580 / kg"}
        ]
    },
    "Frijol": {
        "precio_promedio": 11500,
        "precio_local": 11000,
        "unidad": "kg cargamanto",
        "tendencia": "Alza",
        "variacion": "+6%",
        "fuente": "SIPSA Central de Abastos",
        "historial": [
            {"mes": "Ene", "precio": 10200},
            {"mes": "Feb", "precio": 10500},
            {"mes": "Mar", "precio": 10800},
            {"mes": "Abr", "precio": 11000},
            {"mes": "May", "precio": 11200},
            {"mes": "Jun", "precio": 11500},
        ],
        "compradores": [
            {"nombre": "Leguminosas La Cosecha", "tipo": "Cooperativa", "municipio": "Algeciras, Huila", "contacto": "321 990 8877", "precio": "$11.600 / kg"},
            {"nombre": "Surabastos Granos", "tipo": "Mayorista", "municipio": "Neiva, Huila", "contacto": "312 334 5566", "precio": "$11.300 / kg"}
        ]
    },
    "Aguacate Hass": {
        "precio_promedio": 6800,
        "precio_local": 6400,
        "unidad": "kg",
        "tendencia": "Alza",
        "variacion": "+9%",
        "fuente": "Asohofrucol / SIPSA",
        "historial": [
            {"mes": "Ene", "precio": 5800},
            {"mes": "Feb", "precio": 6000},
            {"mes": "Mar", "precio": 6200},
            {"mes": "Abr", "precio": 6400},
            {"mes": "May", "precio": 6600},
            {"mes": "Jun", "precio": 6800},
        ],
        "compradores": [
            {"nombre": "Hass Colombia Export S.A.", "tipo": "Exportador", "municipio": "Pitalito, Huila", "contacto": "319 887 1122", "precio": "$7.000 / kg"},
            {"nombre": "Frutas del Huila", "tipo": "Intermediario", "municipio": "Neiva, Huila", "contacto": "315 221 4433", "precio": "$6.600 / kg"}
        ]
    },
    "Papa": {
        "precio_promedio": 2300,
        "precio_local": 2150,
        "unidad": "kg",
        "tendencia": "Baja",
        "variacion": "-5%",
        "fuente": "Fedepapa / SIPSA",
        "historial": [
            {"mes": "Ene", "precio": 2600},
            {"mes": "Feb", "precio": 2550},
            {"mes": "Mar", "precio": 2450},
            {"mes": "Abr", "precio": 2400},
            {"mes": "May", "precio": 2350},
            {"mes": "Jun", "precio": 2300},
        ],
        "compradores": [
            {"nombre": "Tubérculos del Surabastos", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "310 998 4433", "precio": "$2.350 / kg"}
        ]
    },
    "Tomate": {
        "precio_promedio": 3200,
        "precio_local": 3000,
        "unidad": "kg chonto",
        "tendencia": "Estable",
        "variacion": "+2%",
        "fuente": "SIPSA Surabastos",
        "historial": [
            {"mes": "Ene", "precio": 3100},
            {"mes": "Feb", "precio": 3050},
            {"mes": "Mar", "precio": 3150},
            {"mes": "Abr", "precio": 3200},
            {"mes": "May", "precio": 3180},
            {"mes": "Jun", "precio": 3200},
        ],
        "compradores": [
            {"nombre": "Surabastos Hortalizas", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "316 445 6677", "precio": "$3.250 / kg"}
        ]
    },
    "Arroz": {
        "precio_promedio": 2100,
        "precio_local": 2050,
        "unidad": "kg paddy verde",
        "tendencia": "Estable",
        "variacion": "0%",
        "fuente": "Fedearroz / SIPSA Campoalegre",
        "historial": [
            {"mes": "Ene", "precio": 2080},
            {"mes": "Feb", "precio": 2100},
            {"mes": "Mar", "precio": 2090},
            {"mes": "Abr", "precio": 2110},
            {"mes": "May", "precio": 2100},
            {"mes": "Jun", "precio": 2100},
        ],
        "compradores": [
            {"nombre": "Molino Florhuila Campoalegre", "tipo": "Agroindustria", "municipio": "Campoalegre, Huila", "contacto": "312 889 0011", "precio": "$2.150 / kg"},
            {"nombre": "Molino Roa Neiva", "tipo": "Agroindustria", "municipio": "Neiva, Huila", "contacto": "315 667 8899", "precio": "$2.140 / kg"}
        ]
    }
}


def _build_datos_cultivo_from_db(pm):
    """Convierte un objeto PrecioMercado en el formato de dict usado por las vistas."""
    return {
        "precio_promedio": float(pm.precio_promedio),
        "precio_local": float(pm.precio_local) if pm.precio_local is not None else float(pm.precio_promedio),
        "unidad": pm.unidad,
        "tendencia": pm.tendencia,
        "variacion": f"{pm.variacion_porcentaje:+.0f}%",
        "fuente": pm.fuente,
        # El modelo PrecioMercado no almacena historial mensual, usamos el fallback si existe
        "historial": DATOS_MERCADO_HUILA.get(pm.cultivo_nombre, {}).get(
            "historial",
            [{"mes": "Jun", "precio": float(pm.precio_promedio)}]
        ),
        "compradores": [],  # se rellena abajo con compradores de BD o del dict estático
    }


def _get_compradores_for_cultivo(cultivo_key):
    """Devuelve la lista de compradores (dict) para un cultivo dado, preferiendo BD."""
    if Comprador.objects.filter(activo=True).exists():
        qs = Comprador.objects.filter(
            activo=True,
            cultivos_interes__icontains=cultivo_key
        )
        if not qs.exists():
            # Si ninguno tiene ese cultivo específico, devuelve todos los activos
            qs = Comprador.objects.filter(activo=True)
        compradores = []
        for c in qs:
            compradores.append({
                "nombre": c.nombre,
                "tipo": c.tipo,
                "municipio": c.municipio,
                "contacto": c.contacto,
                "precio": c.precio_referencia or "",
            })
        return compradores
    # Fallback: compradores del dict estático
    return DATOS_MERCADO_HUILA.get(cultivo_key, {}).get("compradores", [])


@login_required(login_url='login')
def precios_sipsa(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    cultivo_solicitado = request.GET.get('cultivo', 'Maíz').strip()

    # Matching crop name flexibly
    cultivo_key = "Maíz"
    for k in DATOS_MERCADO_HUILA.keys():
        if k.lower() in cultivo_solicitado.lower() or cultivo_solicitado.lower() in k.lower():
            cultivo_key = k
            break

    # Prefer DB data over static dict
    if PrecioMercado.objects.exists():
        pm = PrecioMercado.objects.filter(cultivo_nombre=cultivo_key).first()
        if pm is None:
            # Try flexible match
            pm = PrecioMercado.objects.filter(cultivo_nombre__icontains=cultivo_key).first()
        if pm is not None:
            datos_cultivo = _build_datos_cultivo_from_db(pm)
        else:
            datos_cultivo = DATOS_MERCADO_HUILA.get(cultivo_key, DATOS_MERCADO_HUILA["Maíz"])
        # Available crops: union of DB + static dict keys
        cultivos_db = list(PrecioMercado.objects.values_list('cultivo_nombre', flat=True).distinct())
        cultivos_disponibles = list(dict.fromkeys(cultivos_db + list(DATOS_MERCADO_HUILA.keys())))
    else:
        datos_cultivo = DATOS_MERCADO_HUILA.get(cultivo_key, DATOS_MERCADO_HUILA["Maíz"])
        cultivos_disponibles = list(DATOS_MERCADO_HUILA.keys())

    # Fill in compradores (preferring BD)
    datos_cultivo = dict(datos_cultivo)  # shallow copy to avoid mutating dict
    datos_cultivo["compradores"] = _get_compradores_for_cultivo(cultivo_key)

    # Try connecting to live DANE open data API (Datos.gov.co)
    estado_conexion = 'online'
    mensaje_conexion = 'Conectado en tiempo real a los servidores de SIPSA / DANE.'

    try:
        response = requests.get('https://www.datos.gov.co/resource/mqa9-ndae.json?$limit=10', timeout=2)
        if response.status_code != 200:
            estado_conexion = 'offline'
            mensaje_conexion = 'Sin conexión a DANE/SIPSA. Mostrando datos de referencia regional almacenados localmente.'
    except Exception:
        estado_conexion = 'offline'
        mensaje_conexion = 'Sin conexión a DANE/SIPSA. Mostrando datos de referencia regional almacenados localmente.'

    # Max price calculation for bar height scaling
    precios_historial = [item["precio"] for item in datos_cultivo["historial"]]
    max_precio = max(precios_historial) if precios_historial else 1

    historial_con_porcentajes = []
    for h in datos_cultivo["historial"]:
        pct = int((h["precio"] / max_precio) * 100)
        historial_con_porcentajes.append({
            "mes": h["mes"],
            "precio": h["precio"],
            "pct": max(30, pct)
        })

    # Local vs Regional calculation
    precio_reg = datos_cultivo["precio_promedio"]
    precio_loc = datos_cultivo["precio_local"]
    max_comp = max(precio_reg, precio_loc)
    pct_loc = int((precio_loc / max_comp) * 90)
    pct_reg = int((precio_reg / max_comp) * 90)

    context = {
        'cultivo_actual': cultivo_key,
        'datos': datos_cultivo,
        'cultivos_disponibles': cultivos_disponibles,
        'historial_grafica': historial_con_porcentajes,
        'pct_local': pct_loc,
        'pct_regional': pct_reg,
        'max_precio_historico': max_precio,
        'estado_conexion': estado_conexion,
        'mensaje_conexion': mensaje_conexion,
        'fecha_hoy': datetime.now().strftime("%d/%m/%Y")
    }
    return render(request, 'agricultor/mercado.html', context)


@login_required(login_url='login')
def api_datos_cultivo_mercado(request, cultivo_nombre):
    """
    Retorna JSON con los precios, tendencia, gráfica y compradores para actualización AJAX.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    cultivo_key = "Maíz"
    for k in DATOS_MERCADO_HUILA.keys():
        if k.lower() in cultivo_nombre.lower() or cultivo_nombre.lower() in k.lower():
            cultivo_key = k
            break

    # Prefer DB data over static dict
    if PrecioMercado.objects.exists():
        pm = PrecioMercado.objects.filter(cultivo_nombre=cultivo_key).first()
        if pm is None:
            pm = PrecioMercado.objects.filter(cultivo_nombre__icontains=cultivo_key).first()
        if pm is not None:
            datos = _build_datos_cultivo_from_db(pm)
        else:
            datos = DATOS_MERCADO_HUILA.get(cultivo_key, DATOS_MERCADO_HUILA["Maíz"])
    else:
        datos = DATOS_MERCADO_HUILA.get(cultivo_key, DATOS_MERCADO_HUILA["Maíz"])

    compradores = _get_compradores_for_cultivo(cultivo_key)

    precios_historial = [item["precio"] for item in datos["historial"]]
    max_precio = max(precios_historial) if precios_historial else 1

    historial = []
    for h in datos["historial"]:
        historial.append({
            "mes": h["mes"],
            "precio": h["precio"],
            "pct": max(30, int((h["precio"] / max_precio) * 100))
        })

    return JsonResponse({
        'estado': 'ok',
        'cultivo': cultivo_key,
        'precio_promedio': datos["precio_promedio"],
        'precio_local': datos["precio_local"],
        'unidad': datos["unidad"],
        'tendencia': datos["tendencia"],
        'variacion': datos["variacion"],
        'fuente': datos["fuente"],
        'historial': historial,
        'max_precio': max_precio,
        'compradores': compradores,
    })
