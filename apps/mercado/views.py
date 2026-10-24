from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from io import StringIO
import unicodedata

from apps.sipsa.models import PrecioSemanal
from .models import Comprador

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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
    },
    "Cacao (pasta)": {
        "precio_promedio": 25000,
        "precio_local": 24000,
        "unidad": "kg pasta",
        "tendencia": "Alza",
        "variacion": "+18%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 20000},
            {"mes": "Feb", "precio": 20800},
            {"mes": "Mar", "precio": 21600},
            {"mes": "Abr", "precio": 22400},
            {"mes": "May", "precio": 23000},
            {"mes": "Jun", "precio": 23500},
            {"mes": "Jul", "precio": 24000},
            {"mes": "Ago", "precio": 24300},
            {"mes": "Sep", "precio": 24650},
            {"mes": "Oct", "precio": 25000},
        ],
        "compradores": [
            {"nombre": "Chocolatería y Derivados del Huila", "tipo": "Transformador", "municipio": "Gigante, Huila", "contacto": "314 332 1100", "precio": "$25.500 / kg"},
            {"nombre": "CADEFIHUILA", "tipo": "Cooperativa", "municipio": "Neiva / Garzón", "contacto": "310 555 4321", "precio": "$25.000 / kg"},
            {"nombre": "Industrias Cacao Sur S.A.S.", "tipo": "Agroindustria", "municipio": "Pitalito, Huila", "contacto": "319 887 4455", "precio": "$25.200 / kg"},
        ]
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
        ]
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
        ]
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
        ]
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
        ]
    },
    "Aguacate Hass (exportación)": {
        "precio_promedio": 8500,
        "precio_local": 8000,
        "unidad": "kg exportación",
        "tendencia": "Alza",
        "variacion": "+15%",
        "fuente": "SIPSA — Mercado Regional Huila",
        "historial": [
            {"mes": "Ene", "precio": 6800},
            {"mes": "Feb", "precio": 7050},
            {"mes": "Mar", "precio": 7300},
            {"mes": "Abr", "precio": 7550},
            {"mes": "May", "precio": 7750},
            {"mes": "Jun", "precio": 7950},
            {"mes": "Jul", "precio": 8100},
            {"mes": "Ago", "precio": 8200},
            {"mes": "Sep", "precio": 8350},
            {"mes": "Oct", "precio": 8500},
        ],
        "compradores": [
            {"nombre": "Hass Colombia Export S.A.", "tipo": "Exportador", "municipio": "Pitalito, Huila", "contacto": "319 887 1122", "precio": "$8.800 / kg"},
            {"nombre": "CADEFIHUILA", "tipo": "Cooperativa", "municipio": "Neiva / Garzón", "contacto": "310 555 4321", "precio": "$8.500 / kg"},
            {"nombre": "Asohofrucol Huila", "tipo": "Asociación", "municipio": "Neiva, Huila", "contacto": "311 667 8899", "precio": "$8.300 / kg"},
            {"nombre": "Exportaciones Frutas Huila S.A.S.", "tipo": "Exportador", "municipio": "Pitalito, Huila", "contacto": "316 778 9900", "precio": "$8.700 / kg"},
        ]
    },
}


def _normalizar_tendencia(valor):
    mapping = {
        'sube': 'Alza',
        'alza': 'Alza',
        'baja': 'Baja',
        'estable': 'Estable',
    }
    return mapping.get(str(valor or '').strip().lower(), valor or 'Estable')


def _get_compradores_for_cultivo(cultivo_key):
    """Devuelve la lista de compradores (dict) para un cultivo dado, preferiendo BD relacional."""
    qs = Comprador.objects.filter(activo=True, cultivos_rel__nombre__icontains=cultivo_key).distinct()
    if qs.exists():
        compradores = []
        for c in qs:
            compradores.append({
                "nombre": c.nombre,
                "tipo": c.tipo,
                "municipio": c.municipio,
                "contacto": c.contacto,
                "precio": c.precio_referencia or "",
                "email": c.email,
                "whatsapp": c.whatsapp,
                "sitio_web": c.sitio_web,
            })
        return compradores
    return DATOS_MERCADO_HUILA.get(cultivo_key, {}).get("compradores", [])


def _normalizar_texto(s):
    """Quita tildes y convierte a minúsculas para comparación flexible."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def _resolver_cultivo_key(nombre):
    solicitado_raw = (nombre or 'Maíz').strip() or 'Maíz'
    solicitado = _normalizar_texto(solicitado_raw)
    cultivo_key = "Maíz"
    for k in DATOS_MERCADO_HUILA.keys():
        k_norm = _normalizar_texto(k)
        if k_norm in solicitado or solicitado in k_norm:
            cultivo_key = k
            break
    return cultivo_key


def _datos_cultivo(cultivo_key):
    return DATOS_MERCADO_HUILA.get(cultivo_key, DATOS_MERCADO_HUILA["Maíz"])


def _listado_precios_tabla():
    precios = []
    for nombre, datos in DATOS_MERCADO_HUILA.items():
        precios.append({
            "cultivo": nombre,
            "precio": f"${datos['precio_promedio']:,.0f} / {datos['unidad']}",
            "tendencia": datos.get("tendencia", "Estable"),
            "mercado": "Huila",
        })
    return precios


@login_required(login_url='login')
def precios_sipsa(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    cultivo_key = _resolver_cultivo_key(request.GET.get('cultivo', 'Maíz'))
    datos_cultivo = dict(_datos_cultivo(cultivo_key))
    datos_cultivo["compradores"] = _get_compradores_for_cultivo(cultivo_key)
    datos_cultivo["tendencia"] = _normalizar_tendencia(datos_cultivo.get("tendencia"))

    cultivos_disponibles = list(DATOS_MERCADO_HUILA.keys())

    # Indicador de estado de conexión
    hace_24h = timezone.now() - timedelta(hours=24)
    hace_72h = timezone.now() - timedelta(hours=72)

    ps_mas_reciente = PrecioSemanal.objects.order_by('-fecha_registro').first()
    ultima_actualizacion_global = None

    if ps_mas_reciente and ps_mas_reciente.fecha_registro:
        ts = ps_mas_reciente.fecha_registro
        dias_desde = (timezone.now() - ts).days
        ultima_actualizacion_global = timezone.localtime(ts).strftime("%d/%m/%Y %H:%M")

        if ts >= hace_24h:
            estado_conexion = 'online'
            mensaje_conexion = f"Precios actualizados al {ultima_actualizacion_global} desde SIPSA/DANE."
        elif ts >= hace_72h:
            estado_conexion = 'reciente'
            mensaje_conexion = f"Precios con {dias_desde} día(s) de antigüedad. Se recomienda actualizar."
        else:
            estado_conexion = 'desactualizado'
            mensaje_conexion = f"Precios con más de 72h de antigüedad ({dias_desde} días). Mostrando datos de referencia."
    else:
        estado_conexion = 'reciente'
        mensaje_conexion = "Mostrando precios oficiales y de referencia regional Huila."

    precios_tabla = []
    for nombre_cultivo in cultivos_disponibles:
        datos_est = DATOS_MERCADO_HUILA.get(nombre_cultivo, {})
        if datos_est:
            precios_tabla.append({
                "cultivo": nombre_cultivo,
                "precio_promedio": datos_est.get("precio_promedio", 0),
                "precio_local": datos_est.get("precio_local", datos_est.get("precio_promedio", 0)),
                "unidad": datos_est.get("unidad", "kg"),
                "tendencia": _normalizar_tendencia(datos_est.get("tendencia", "Estable")),
                "variacion_porcentaje": float(
                    str(datos_est.get("variacion", "0%")).replace('%', '').replace('+', '')
                ),
                "fuente": datos_est.get("fuente", "SIPSA / DANE"),
                "ultima_actualizacion": "—",
                "dias_desde_actualizacion": None,
                "compradores": _get_compradores_for_cultivo(nombre_cultivo),
                "historial": datos_est.get("historial", []),
            })

    precios_historial = [item["precio"] for item in datos_cultivo.get("historial", [])]
    max_precio = max(precios_historial) if precios_historial else 1

    historial_con_porcentajes = []
    for h in datos_cultivo.get("historial", []):
        pct = int((h["precio"] / max_precio) * 100) if max_precio else 30
        historial_con_porcentajes.append({
            "mes": h["mes"],
            "precio": h["precio"],
            "pct": max(30, pct)
        })

    precio_reg = float(datos_cultivo.get("precio_promedio") or 0)
    precio_loc = float(datos_cultivo.get("precio_local") or 0)
    max_comp = max(precio_reg, precio_loc, 1)
    pct_loc = int((precio_loc / max_comp) * 90)
    pct_reg = int((precio_reg / max_comp) * 90)

    context = {
        'cultivo_actual': cultivo_key,
        'datos': datos_cultivo,
        'precios': _listado_precios_tabla(),
        'precios_tabla': precios_tabla,
        'cultivos_disponibles': cultivos_disponibles,
        'historial_grafica': historial_con_porcentajes,
        'pct_local': pct_loc,
        'pct_regional': pct_reg,
        'max_precio_historico': max_precio,
        'estado_conexion': estado_conexion,
        'mensaje_conexion': mensaje_conexion,
        'ultima_actualizacion_global': ultima_actualizacion_global,
        'fecha_hoy': datetime.now().strftime("%d/%m/%Y")
    }
    return render(request, 'agricultor/precios_sipsa.html', context)


@login_required(login_url='login')
def actualizar_precios_view(request):
    """Dispara el comando actualizar_precios vía POST y devuelve JSON con el resultado."""
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    out = StringIO()
    try:
        from django.core.management import call_command
        call_command('actualizar_sipsa', stdout=out)
        return JsonResponse({'status': 'ok', 'output': out.getvalue()})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)


@login_required(login_url='login')
def api_datos_cultivo_mercado(request, cultivo_nombre):
    """
    Retorna JSON con los precios, tendencia, gráfica y compradores para actualización AJAX.
    """
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    cultivo_key = _resolver_cultivo_key(cultivo_nombre)
    datos = dict(_datos_cultivo(cultivo_key))
    datos["tendencia"] = _normalizar_tendencia(datos.get("tendencia"))
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


@login_required(login_url='login')
def listado_productos(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    return render(request, 'agricultor/mercado.html', {'productos': []})


@login_required(login_url='login')
def mi_tienda(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return redirect('home')

    return render(request, 'agricultor/mi_tienda.html', {'productos': []})


@login_required(login_url='login')
def agregar_producto(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    return JsonResponse({'mensaje': 'Módulo de productos actualizado.'})


@login_required(login_url='login')
def eliminar_producto(request, producto_id):
    if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
        return JsonResponse({'error': 'No autorizado'}, status=403)

    return JsonResponse({'mensaje': 'Producto eliminado.'})
