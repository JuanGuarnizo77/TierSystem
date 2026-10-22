"""
Management command: seed_mercado
Populates PrecioMercado and Comprador tables from the static DATOS_MERCADO_HUILA dict.
Idempotent — uses update_or_create, safe to run multiple times.
Also links the FK PrecioMercado.cultivo → CultivoSipsa for each canonical crop name.

Usage:
    python manage.py seed_mercado
"""
from django.core.management.base import BaseCommand

from apps.mercado.models import PrecioMercado, Comprador
from apps.sipsa.models import CultivoSipsa

# Catálogo base de precios de referencia regional Huila (SIPSA/DANE)
# Moved here from views.py — this is the authoritative seed source; views read from DB.
DATOS_MERCADO_HUILA = {
    "Maíz Amarillo": {
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
            {"nombre": "Granos & Cereales del Sur", "tipo": "Exportador", "municipio": "Pitalito, Huila", "contacto": "318 998 7766", "precio": "$1.480 / kg"},
        ],
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
            {"nombre": "Café Especial La Angostura", "tipo": "Comprador Especial", "municipio": "Campoalegre, Huila", "contacto": "311 223 3445", "precio": "$18.800 / kg"},
        ],
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
            {"nombre": "Surabastos Cacao Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "316 887 4455", "precio": "$20.800 / kg"},
        ],
    },
    "Fríjol Cargamanto": {
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
            {"nombre": "Surabastos Granos", "tipo": "Mayorista", "municipio": "Neiva, Huila", "contacto": "312 334 5566", "precio": "$11.300 / kg"},
        ],
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
            {"nombre": "Frutas del Huila", "tipo": "Intermediario", "municipio": "Neiva, Huila", "contacto": "315 221 4433", "precio": "$6.600 / kg"},
        ],
    },
    "Papa Pastusa": {
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
            {"nombre": "Tubérculos del Surabastos", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "310 998 4433", "precio": "$2.350 / kg"},
        ],
    },
    "Tomate Chonto": {
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
            {"nombre": "Surabastos Hortalizas", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "316 445 6677", "precio": "$3.250 / kg"},
        ],
    },
    "Arroz Blanco": {
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
            {"nombre": "Molino Roa Neiva", "tipo": "Agroindustria", "municipio": "Neiva, Huila", "contacto": "315 667 8899", "precio": "$2.140 / kg"},
        ],
    },
    # ── Cultivos ampliados Huila ─────────────────────────────────────────────
    "Yuca": {
        "precio_promedio": 980,
        "precio_local": 900,
        "unidad": "kg",
        "tendencia": "Estable",
        "variacion": "+2%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 820},
            {"mes": "Feb", "precio": 840},
            {"mes": "Mar", "precio": 860},
            {"mes": "Abr", "precio": 880},
            {"mes": "May", "precio": 900},
            {"mes": "Jun", "precio": 920},
            {"mes": "Jul", "precio": 940},
            {"mes": "Ago", "precio": 950},
            {"mes": "Sep", "precio": 965},
            {"mes": "Oct", "precio": 980},
        ],
        "compradores": [
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$990 / kg"},
            {"nombre": "Cooperativa Productores Huila", "tipo": "Cooperativa", "municipio": "Garzón, Huila", "contacto": "317 456 7890", "precio": "$970 / kg"},
            {"nombre": "Agrocomercial del Huila S.A.S.", "tipo": "Intermediario", "municipio": "Neiva, Huila", "contacto": "320 112 3344", "precio": "$960 / kg"},
        ],
    },
    "Plátano Hartón": {
        "precio_promedio": 1800,
        "precio_local": 1700,
        "unidad": "kg",
        "tendencia": "Alza",
        "variacion": "+5%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 1480},
            {"mes": "Feb", "precio": 1520},
            {"mes": "Mar", "precio": 1560},
            {"mes": "Abr", "precio": 1600},
            {"mes": "May", "precio": 1640},
            {"mes": "Jun", "precio": 1680},
            {"mes": "Jul", "precio": 1710},
            {"mes": "Ago", "precio": 1740},
            {"mes": "Sep", "precio": 1770},
            {"mes": "Oct", "precio": 1800},
        ],
        "compradores": [
            {"nombre": "Distribuidora Plátano Verde Huila", "tipo": "Mayorista", "municipio": "Garzón, Huila", "contacto": "313 776 5544", "precio": "$1.820 / kg"},
            {"nombre": "Surabastos Pabellón Frutas", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "318 443 2211", "precio": "$1.790 / kg"},
            {"nombre": "Frigorífico del Sur", "tipo": "Agroindustria", "municipio": "Pitalito, Huila", "contacto": "314 998 1122", "precio": "$1.760 / kg"},
        ],
    },
    "Aguacate Común": {
        "precio_promedio": 3200,
        "precio_local": 3000,
        "unidad": "kg",
        "tendencia": "Alza",
        "variacion": "+4%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 2640},
            {"mes": "Feb", "precio": 2720},
            {"mes": "Mar", "precio": 2800},
            {"mes": "Abr", "precio": 2880},
            {"mes": "May", "precio": 2960},
            {"mes": "Jun", "precio": 3020},
            {"mes": "Jul", "precio": 3060},
            {"mes": "Ago", "precio": 3100},
            {"mes": "Sep", "precio": 3150},
            {"mes": "Oct", "precio": 3200},
        ],
        "compradores": [
            {"nombre": "Asohofrucol Huila", "tipo": "Asociación", "municipio": "Neiva, Huila", "contacto": "311 667 8899", "precio": "$3.250 / kg"},
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$3.100 / kg"},
            {"nombre": "Plaza Garzón", "tipo": "Plaza Minorista", "municipio": "Garzón, Huila", "contacto": "318 334 5566", "precio": "$3.050 / kg"},
        ],
    },
    "Caña Panelera": {
        "precio_promedio": 4200,
        "precio_local": 4000,
        "unidad": "kg panela",
        "tendencia": "Estable",
        "variacion": "+1%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 3570},
            {"mes": "Feb", "precio": 3650},
            {"mes": "Mar", "precio": 3750},
            {"mes": "Abr", "precio": 3850},
            {"mes": "May", "precio": 3950},
            {"mes": "Jun", "precio": 4000},
            {"mes": "Jul", "precio": 4050},
            {"mes": "Ago", "precio": 4100},
            {"mes": "Sep", "precio": 4150},
            {"mes": "Oct", "precio": 4200},
        ],
        "compradores": [
            {"nombre": "CADEFIHUILA", "tipo": "Cooperativa", "municipio": "Neiva / Garzón", "contacto": "310 555 4321", "precio": "$4.250 / kg"},
            {"nombre": "Supermercados Merca", "tipo": "Supermercado", "municipio": "Neiva, Huila", "contacto": "312 445 6678", "precio": "$4.100 / kg"},
            {"nombre": "Cooperativa Productores Huila", "tipo": "Cooperativa", "municipio": "Pitalito, Huila", "contacto": "317 456 7890", "precio": "$4.050 / kg"},
        ],
    },
    "Maracuyá": {
        "precio_promedio": 2800,
        "precio_local": 2600,
        "unidad": "kg",
        "tendencia": "Alza",
        "variacion": "+7%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 2240},
            {"mes": "Feb", "precio": 2330},
            {"mes": "Mar", "precio": 2420},
            {"mes": "Abr", "precio": 2510},
            {"mes": "May", "precio": 2580},
            {"mes": "Jun", "precio": 2630},
            {"mes": "Jul", "precio": 2680},
            {"mes": "Ago", "precio": 2720},
            {"mes": "Sep", "precio": 2760},
            {"mes": "Oct", "precio": 2800},
        ],
        "compradores": [
            {"nombre": "Asohofrucol Huila", "tipo": "Asociación", "municipio": "Neiva, Huila", "contacto": "311 667 8899", "precio": "$2.850 / kg"},
            {"nombre": "Jugos Tropicales del Sur", "tipo": "Agroindustria", "municipio": "Campoalegre, Huila", "contacto": "314 223 4455", "precio": "$2.780 / kg"},
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$2.700 / kg"},
        ],
    },
    "Lulo": {
        "precio_promedio": 3500,
        "precio_local": 3200,
        "unidad": "kg",
        "tendencia": "Estable",
        "variacion": "+3%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 2975},
            {"mes": "Feb", "precio": 3050},
            {"mes": "Mar", "precio": 3100},
            {"mes": "Abr", "precio": 3150},
            {"mes": "May", "precio": 3200},
            {"mes": "Jun", "precio": 3280},
            {"mes": "Jul", "precio": 3320},
            {"mes": "Ago", "precio": 3360},
            {"mes": "Sep", "precio": 3430},
            {"mes": "Oct", "precio": 3500},
        ],
        "compradores": [
            {"nombre": "Asohofrucol Huila", "tipo": "Asociación", "municipio": "Neiva, Huila", "contacto": "311 667 8899", "precio": "$3.550 / kg"},
            {"nombre": "Plaza Garzón", "tipo": "Plaza Minorista", "municipio": "Garzón, Huila", "contacto": "318 334 5566", "precio": "$3.400 / kg"},
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$3.350 / kg"},
        ],
    },
    "Cholupa": {
        "precio_promedio": 4500,
        "precio_local": 4200,
        "unidad": "kg",
        "tendencia": "Alza",
        "variacion": "+10%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 3600},
            {"mes": "Feb", "precio": 3720},
            {"mes": "Mar", "precio": 3840},
            {"mes": "Abr", "precio": 3960},
            {"mes": "May", "precio": 4080},
            {"mes": "Jun", "precio": 4170},
            {"mes": "Jul", "precio": 4260},
            {"mes": "Ago", "precio": 4340},
            {"mes": "Sep", "precio": 4420},
            {"mes": "Oct", "precio": 4500},
        ],
        "compradores": [
            {"nombre": "CADEFIHUILA", "tipo": "Cooperativa", "municipio": "Neiva / Garzón", "contacto": "310 555 4321", "precio": "$4.600 / kg"},
            {"nombre": "Asohofrucol Huila", "tipo": "Asociación", "municipio": "Neiva, Huila", "contacto": "311 667 8899", "precio": "$4.500 / kg"},
            {"nombre": "Exportaciones Frutas Huila S.A.S.", "tipo": "Exportador", "municipio": "Pitalito, Huila", "contacto": "316 778 9900", "precio": "$4.800 / kg"},
        ],
    },
    "Sorgo": {
        "precio_promedio": 1100,
        "precio_local": 1050,
        "unidad": "kg",
        "tendencia": "Estable",
        "variacion": "0%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 1050},
            {"mes": "Feb", "precio": 1060},
            {"mes": "Mar", "precio": 1060},
            {"mes": "Abr", "precio": 1070},
            {"mes": "May", "precio": 1080},
            {"mes": "Jun", "precio": 1090},
            {"mes": "Jul", "precio": 1090},
            {"mes": "Ago", "precio": 1095},
            {"mes": "Sep", "precio": 1100},
            {"mes": "Oct", "precio": 1100},
        ],
        "compradores": [
            {"nombre": "Granos & Cereales del Sur", "tipo": "Exportador", "municipio": "Pitalito, Huila", "contacto": "318 998 7766", "precio": "$1.120 / kg"},
            {"nombre": "Agrocomercial del Huila S.A.S.", "tipo": "Intermediario", "municipio": "Garzón, Huila", "contacto": "320 112 3344", "precio": "$1.100 / kg"},
        ],
    },
    "Limón Tahití": {
        "precio_promedio": 1800,
        "precio_local": 1700,
        "unidad": "kg",
        "tendencia": "Alza",
        "variacion": "+6%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 1440},
            {"mes": "Feb", "precio": 1500},
            {"mes": "Mar", "precio": 1560},
            {"mes": "Abr", "precio": 1600},
            {"mes": "May", "precio": 1640},
            {"mes": "Jun", "precio": 1680},
            {"mes": "Jul", "precio": 1710},
            {"mes": "Ago", "precio": 1740},
            {"mes": "Sep", "precio": 1770},
            {"mes": "Oct", "precio": 1800},
        ],
        "compradores": [
            {"nombre": "Asohofrucol Huila", "tipo": "Asociación", "municipio": "Neiva, Huila", "contacto": "311 667 8899", "precio": "$1.850 / kg"},
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$1.800 / kg"},
            {"nombre": "Cooperativa Productores Huila", "tipo": "Cooperativa", "municipio": "Rivera, Huila", "contacto": "317 456 7890", "precio": "$1.780 / kg"},
        ],
    },
    "Guanábana": {
        "precio_promedio": 3800,
        "precio_local": 3500,
        "unidad": "kg",
        "tendencia": "Estable",
        "variacion": "+2%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 3230},
            {"mes": "Feb", "precio": 3300},
            {"mes": "Mar", "precio": 3380},
            {"mes": "Abr", "precio": 3450},
            {"mes": "May", "precio": 3510},
            {"mes": "Jun", "precio": 3570},
            {"mes": "Jul", "precio": 3620},
            {"mes": "Ago", "precio": 3670},
            {"mes": "Sep", "precio": 3730},
            {"mes": "Oct", "precio": 3800},
        ],
        "compradores": [
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$3.850 / kg"},
            {"nombre": "Frutas del Huila", "tipo": "Intermediario", "municipio": "Neiva, Huila", "contacto": "315 221 4433", "precio": "$3.750 / kg"},
            {"nombre": "Plaza Garzón", "tipo": "Plaza Minorista", "municipio": "Garzón, Huila", "contacto": "318 334 5566", "precio": "$3.600 / kg"},
        ],
    },
    "Papaya": {
        "precio_promedio": 1500,
        "precio_local": 1400,
        "unidad": "kg",
        "tendencia": "Baja",
        "variacion": "-3%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 1750},
            {"mes": "Feb", "precio": 1720},
            {"mes": "Mar", "precio": 1680},
            {"mes": "Abr", "precio": 1640},
            {"mes": "May", "precio": 1600},
            {"mes": "Jun", "precio": 1570},
            {"mes": "Jul", "precio": 1550},
            {"mes": "Ago", "precio": 1530},
            {"mes": "Sep", "precio": 1515},
            {"mes": "Oct", "precio": 1500},
        ],
        "compradores": [
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$1.520 / kg"},
            {"nombre": "Frigorífico del Sur", "tipo": "Agroindustria", "municipio": "Pitalito, Huila", "contacto": "314 998 1122", "precio": "$1.480 / kg"},
        ],
    },
    "Mango Tommy": {
        "precio_promedio": 2200,
        "precio_local": 2000,
        "unidad": "kg",
        "tendencia": "Estable",
        "variacion": "+1%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 1870},
            {"mes": "Feb", "precio": 1920},
            {"mes": "Mar", "precio": 1970},
            {"mes": "Abr", "precio": 2020},
            {"mes": "May", "precio": 2060},
            {"mes": "Jun", "precio": 2090},
            {"mes": "Jul", "precio": 2110},
            {"mes": "Ago", "precio": 2140},
            {"mes": "Sep", "precio": 2170},
            {"mes": "Oct", "precio": 2200},
        ],
        "compradores": [
            {"nombre": "Exportaciones Frutas Huila S.A.S.", "tipo": "Exportador", "municipio": "Pitalito, Huila", "contacto": "316 778 9900", "precio": "$2.300 / kg"},
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$2.150 / kg"},
            {"nombre": "Asohofrucol Huila", "tipo": "Asociación", "municipio": "Neiva, Huila", "contacto": "311 667 8899", "precio": "$2.200 / kg"},
        ],
    },
    "Piña Cayena": {
        "precio_promedio": 1600,
        "precio_local": 1500,
        "unidad": "kg",
        "tendencia": "Alza",
        "variacion": "+4%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 1310},
            {"mes": "Feb", "precio": 1360},
            {"mes": "Mar", "precio": 1400},
            {"mes": "Abr", "precio": 1440},
            {"mes": "May", "precio": 1470},
            {"mes": "Jun", "precio": 1490},
            {"mes": "Jul", "precio": 1510},
            {"mes": "Ago", "precio": 1540},
            {"mes": "Sep", "precio": 1570},
            {"mes": "Oct", "precio": 1600},
        ],
        "compradores": [
            {"nombre": "Frigorífico del Sur", "tipo": "Agroindustria", "municipio": "Pitalito, Huila", "contacto": "314 998 1122", "precio": "$1.650 / kg"},
            {"nombre": "Surabastos Neiva", "tipo": "Plaza Mayorista", "municipio": "Neiva, Huila", "contacto": "315 789 1234", "precio": "$1.600 / kg"},
            {"nombre": "Cooperativa Productores Huila", "tipo": "Cooperativa", "municipio": "Garzón, Huila", "contacto": "317 456 7890", "precio": "$1.580 / kg"},
        ],
    },
}





class Command(BaseCommand):
    help = 'Seed PrecioMercado and Comprador tables from the static DATOS_MERCADO_HUILA reference data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== seed_mercado: iniciando siembra de datos ==='))

        precios_creados = 0
        precios_actualizados = 0

        for cultivo_nombre, datos in DATOS_MERCADO_HUILA.items():
            # Parse variation string like "+8%" or "-5%" into float
            variacion_str = datos.get('variacion', '0%').replace('%', '').replace('+', '')
            try:
                variacion_float = float(variacion_str)
            except ValueError:
                variacion_float = 0.0

            pm, created = PrecioMercado.objects.update_or_create(
                cultivo_nombre=cultivo_nombre,
                defaults={
                    'region': 'Huila',
                    'precio_promedio': datos['precio_promedio'],
                    'precio_local': datos.get('precio_local', datos['precio_promedio']),
                    'unidad': datos.get('unidad', 'kg'),
                    'tendencia': datos.get('tendencia', 'Estable'),
                    'variacion_porcentaje': variacion_float,
                    'fuente': datos.get('fuente', 'SIPSA / DANE'),
                }
            )

            # Link FK to canonical CultivoSipsa catalogue
            cultivo_obj = CultivoSipsa.objects.filter(nombre=cultivo_nombre).first()
            if cultivo_obj and pm.cultivo_id != cultivo_obj.pk:
                pm.cultivo = cultivo_obj
                pm.save(update_fields=['cultivo'])

            if created:
                precios_creados += 1
                self.stdout.write(f'  [+] PrecioMercado creado: {cultivo_nombre}')
            else:
                precios_actualizados += 1
                self.stdout.write(f'  [~] PrecioMercado actualizado: {cultivo_nombre}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPrecioMercado — creados: {precios_creados}, actualizados: {precios_actualizados}'
            )
        )

        # ---- Compradores ----
        compradores_creados = 0
        compradores_existentes = 0

        # Collect unique buyers across all crops, tracking which crops each one covers
        compradores_map = {}  # nombre -> {datos, cultivos}
        for cultivo_nombre, datos in DATOS_MERCADO_HUILA.items():
            for c in datos.get('compradores', []):
                nombre = c['nombre']
                if nombre not in compradores_map:
                    compradores_map[nombre] = {
                        'tipo': c.get('tipo', ''),
                        'municipio': c.get('municipio', 'Neiva, Huila'),
                        'contacto': c.get('contacto', ''),
                        'precio_referencia': c.get('precio', ''),
                        'cultivos': [],
                    }
                compradores_map[nombre]['cultivos'].append(cultivo_nombre)

        for nombre, datos_c in compradores_map.items():
            cultivos_interes = ', '.join(datos_c['cultivos'])
            comp, created = Comprador.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'tipo': datos_c['tipo'],
                    'municipio': datos_c['municipio'],
                    'contacto': datos_c['contacto'],
                    'cultivos_interes': cultivos_interes,
                    'precio_referencia': datos_c['precio_referencia'],
                    'activo': True,
                }
            )
            if created:
                compradores_creados += 1
                self.stdout.write(f'  [+] Comprador creado: {nombre}')
            else:
                compradores_existentes += 1
                self.stdout.write(f'  [=] Comprador ya existe: {nombre}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nComprador — creados: {compradores_creados}, ya existían: {compradores_existentes}'
            )
        )

        # ---- Actualizar contactos específicos ----
        cadefi_updated = Comprador.objects.filter(nombre__icontains='CADEFIHUILA').update(
            email='info@cadefihuila.com',
            whatsapp='3105554321',
            sitio_web='https://cadefihuila.com',
        )
        self.stdout.write(
            self.style.SUCCESS(f'  Contactos CADEFIHUILA actualizados: {cadefi_updated} registro(s)')
        )

        surabastos_updated = Comprador.objects.filter(nombre__icontains='Surabastos').update(
            email='comercial@surabastos.com.co',
            whatsapp='3187891234',
            sitio_web='https://surabastos.com.co',
        )
        self.stdout.write(
            self.style.SUCCESS(f'  Contactos Surabastos actualizados: {surabastos_updated} registro(s)')
        )

        self.stdout.write(self.style.SUCCESS('\n=== seed_mercado: completado ==='))
