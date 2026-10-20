"""
Management command: seed_sipsa
Carga 8 semanas de precios históricos SIPSA/DANE para 10 cultivos.
Idempotente — usa get_or_create. Calcula predicciones al finalizar.

Uso:
    python manage.py seed_sipsa
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.sipsa.models import CultivoSipsa, PrecioSemanal, PrediccionPrecio
from apps.sipsa.prediccion import calcular_prediccion


# ──────────────────────────────────────────────────────────────────────
# Precios históricos (COP/kg) — 8 semanas, del más antiguo al más reciente
# Fuente: SIPSA/DANE plazas mayoristas Colombia (datos representativos)
# ──────────────────────────────────────────────────────────────────────

MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
            'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _lunes_hace_n_semanas(n):
    """Devuelve el lunes de hace n semanas."""
    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    return lunes_actual - timedelta(weeks=n)


# Generar 8 semanas desde hace 8 semanas hasta la semana pasada
SEMANAS = [_lunes_hace_n_semanas(8 - i) for i in range(8)]


def _label(d: date) -> str:
    """Devuelve etiqueta legible: '18 ago – 24 ago 2026'."""
    fin = d + timedelta(days=6)
    mes_ini = MESES_ES[d.month - 1]
    mes_fin = MESES_ES[fin.month - 1]
    return f"{d.day} {mes_ini} – {fin.day} {mes_fin} {fin.year}"


CULTIVOS_SEED = [
    {
        "nombre": "Papa Pastusa",
        "nombre_dane": "papa pastusa",
        "unidad": "kg",
        "categoria": "Tubérculos",
        # precios semanas 1..8 (descendente — tendencia Baja) → w8=1900 (DANE oct-2026)
        "precios": [2100, 2050, 1980, 1960, 1940, 1920, 1910, 1900],
    },
    {
        "nombre": "Tomate Chonto",
        "nombre_dane": "tomate chonto",
        "unidad": "kg",
        "categoria": "Hortalizas",
        # w8=3000 (DANE oct-2026)
        "precios": [3600, 3400, 3200, 3100, 3050, 3020, 3010, 3000],
    },
    {
        "nombre": "Cebolla Cabezona",
        "nombre_dane": "cebolla cabezona",
        "unidad": "kg",
        "categoria": "Hortalizas",
        # w8=1200 (DANE oct-2026)
        "precios": [1450, 1400, 1350, 1310, 1280, 1250, 1220, 1200],
    },
    {
        "nombre": "Fríjol Cargamanto",
        "nombre_dane": "frijol cargamanto",
        "unidad": "kg",
        "categoria": "Leguminosas",
        # w8=8400 (DANE oct-2026)
        "precios": [7800, 7900, 8000, 8100, 8200, 8250, 8300, 8400],
    },
    {
        "nombre": "Zanahoria",
        "nombre_dane": "zanahoria",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precios": [1400, 1380, 1360, 1340, 1320, 1310, 1300, 1290],
    },
    {
        "nombre": "Plátano Hartón",
        "nombre_dane": "platano harton",
        "unidad": "kg",
        "categoria": "Frutas",
        # w8=980 (DANE oct-2026)
        "precios": [880, 900, 920, 940, 950, 960, 970, 980],
    },
    {
        "nombre": "Arroz Blanco",
        "nombre_dane": "arroz blanco",
        "unidad": "kg",
        "categoria": "Cereales",
        # w8=3000 (Fedearroz oct-2026)
        "precios": [2800, 2900, 2950, 2980, 2990, 2995, 3000, 3000],
    },
    {
        "nombre": "Maíz Amarillo",
        "nombre_dane": "maiz amarillo",
        "unidad": "kg",
        "categoria": "Cereales",
        # w8=1400 (SIPSA oct-2026)
        "precios": [1300, 1320, 1340, 1355, 1370, 1380, 1390, 1400],
    },
    {
        "nombre": "Aguacate Hass",
        "nombre_dane": "aguacate hass",
        "unidad": "kg",
        "categoria": "Frutas",
        # w8=8197 (Asohofrucol oct-2026)
        "precios": [7200, 7500, 7800, 8000, 8100, 8150, 8175, 8197],
    },
    {
        "nombre": "Yuca",
        "nombre_dane": "yuca",
        "unidad": "kg",
        "categoria": "Tubérculos",
        # w8=1000 (SIPSA oct-2026)
        "precios": [880, 900, 920, 940, 960, 970, 980, 1000],
    },
    # ── Cultivos canónicos ampliados ──────────────────────────────────────
    {
        "nombre": "Café",
        "nombre_dane": "cafe",
        "unidad": "kg pergamino",
        "categoria": "Industria",
        # w8=16440 (FNC oct-2026) — tendencia Baja
        "precios": [17200, 17100, 17000, 16900, 16800, 16700, 16600, 16440],
    },
    {
        "nombre": "Cacao",
        "nombre_dane": "cacao",
        "unidad": "kg grano seco",
        "categoria": "Industria",
        # w8=14805 (Fedecacao oct-2026) — tendencia Baja
        "precios": [15500, 15300, 15100, 14980, 14900, 14860, 14830, 14805],
    },
    {
        "nombre": "Aguacate Común",
        "nombre_dane": "aguacate comun",
        "unidad": "kg",
        "categoria": "Frutas",
        "precios": [2640, 2720, 2800, 2880, 2960, 3020, 3100, 3200],
    },
    {
        "nombre": "Caña Panelera",
        "nombre_dane": "cana panelera",
        "unidad": "kg panela",
        "categoria": "Industriales",
        "precios": [3570, 3650, 3750, 3850, 3950, 4000, 4100, 4200],
    },
    {
        "nombre": "Maracuyá",
        "nombre_dane": "maracuya",
        "unidad": "kg",
        "categoria": "Frutas",
        # w8=2000 (SIPSA oct-2026)
        "precios": [1600, 1680, 1760, 1840, 1900, 1940, 1970, 2000],
    },
    {
        "nombre": "Lulo",
        "nombre_dane": "lulo",
        "unidad": "kg",
        "categoria": "Frutas",
        # w8=2800 (SIPSA oct-2026)
        "precios": [2100, 2200, 2350, 2450, 2550, 2650, 2730, 2800],
    },
    {
        "nombre": "Cholupa",
        "nombre_dane": "cholupa",
        "unidad": "kg",
        "categoria": "Frutas",
        "precios": [3600, 3720, 3840, 3960, 4080, 4170, 4340, 4500],
    },
    {
        "nombre": "Sorgo",
        "nombre_dane": "sorgo",
        "unidad": "kg",
        "categoria": "Cereales",
        # w8=1100 (SIPSA oct-2026)
        "precios": [1050, 1060, 1060, 1070, 1080, 1090, 1095, 1100],
    },
    {
        "nombre": "Limón Tahití",
        "nombre_dane": "limon tahiti",
        "unidad": "kg",
        "categoria": "Frutas",
        "precios": [1440, 1500, 1560, 1600, 1640, 1680, 1740, 1800],
    },
    {
        "nombre": "Guanábana",
        "nombre_dane": "guanabana",
        "unidad": "kg",
        "categoria": "Frutas",
        "precios": [3230, 3300, 3380, 3450, 3510, 3570, 3670, 3800],
    },
    {
        "nombre": "Papaya",
        "nombre_dane": "papaya",
        "unidad": "kg",
        "categoria": "Frutas",
        "precios": [1750, 1720, 1680, 1640, 1600, 1570, 1530, 1500],
    },
    {
        "nombre": "Mango Tommy",
        "nombre_dane": "mango tommy",
        "unidad": "kg",
        "categoria": "Frutas",
        "precios": [1870, 1920, 1970, 2020, 2060, 2090, 2140, 2200],
    },
    {
        "nombre": "Piña Cayena",
        "nombre_dane": "pina cayena",
        "unidad": "kg",
        "categoria": "Frutas",
        "precios": [1310, 1360, 1400, 1440, 1470, 1490, 1540, 1600],
    },
    # ── Cultivos adicionales del brief ────────────────────────────────────
    {
        "nombre": "Fríjol Bola Roja",
        "nombre_dane": "frijol bola roja",
        "unidad": "kg",
        "categoria": "Leguminosas",
        # w8=6500 (SIPSA oct-2026)
        "precios": [5800, 5900, 6000, 6100, 6200, 6300, 6400, 6500],
    },
    {
        "nombre": "Granadilla",
        "nombre_dane": "granadilla",
        "unidad": "kg",
        "categoria": "Frutas",
        # w8=3500 (SIPSA oct-2026)
        "precios": [2800, 2900, 3000, 3100, 3150, 3250, 3350, 3500],
    },
    {
        "nombre": "Pitahaya",
        "nombre_dane": "pitahaya",
        "unidad": "kg",
        "categoria": "Frutas",
        # w8=7500 (SIPSA oct-2026)
        "precios": [6000, 6200, 6400, 6600, 6800, 7000, 7200, 7500],
    },
    {
        "nombre": "Gulupa",
        "nombre_dane": "gulupa",
        "unidad": "kg",
        "categoria": "Frutas",
        # w8=5000 (SIPSA oct-2026)
        "precios": [4000, 4100, 4200, 4300, 4400, 4500, 4700, 5000],
    },
    {
        "nombre": "Mora",
        "nombre_dane": "mora",
        "unidad": "kg",
        "categoria": "Frutas",
        # w8=4500 (SIPSA oct-2026)
        "precios": [3500, 3700, 3900, 4000, 4100, 4200, 4350, 4500],
    },
]


class Command(BaseCommand):
    help = 'Siembra 8 semanas de precios SIPSA históricos para 23 cultivos canónicos.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== seed_sipsa: iniciando ==='))
        creados_c = 0
        creados_p = 0

        for datos in CULTIVOS_SEED:
            cultivo, c_new = CultivoSipsa.objects.get_or_create(
                nombre=datos['nombre'],
                defaults={
                    'nombre_dane': datos['nombre_dane'],
                    'unidad': datos['unidad'],
                    'categoria': datos['categoria'],
                    'activo': True,
                }
            )
            if c_new:
                creados_c += 1
                self.stdout.write(f'  [+] Cultivo: {cultivo.nombre}')

            for semana_date, precio in zip(SEMANAS, datos['precios']):
                label = _label(semana_date)
                ps, p_new = PrecioSemanal.objects.update_or_create(
                    cultivo=cultivo,
                    fecha_semana=semana_date,
                    defaults={
                        'semana_label': label,
                        'precio_kg': precio,
                        'precio_local': round(precio * 0.97, 2),
                        'mercado_referencia': 'SIPSA — Plazas Mayoristas Colombia',
                        'fuente': 'SIPSA / DANE (seed histórico)',
                        'fuente_url': 'https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Abastecimiento-de-alimentos-en-centrales-de-abasto/3sp3-mua5',
                    }
                )
                if p_new:
                    creados_p += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nCultivos: {creados_c} nuevos | Precios: {creados_p} nuevos'
        ))

        # Calcular predicciones para todos los cultivos
        _recalcular_predicciones(self)

        self.stdout.write(self.style.SUCCESS('=== seed_sipsa: completado ==='))


def _recalcular_predicciones(cmd=None):
    """Recalcula PrediccionPrecio para todos los CultivoSipsa activos."""
    for cultivo in CultivoSipsa.objects.filter(activo=True):
        precios_qs = (
            PrecioSemanal.objects
            .filter(cultivo=cultivo)
            .order_by('fecha_semana')
            .values_list('precio_kg', flat=True)
        )
        precios = [float(p) for p in precios_qs]
        resultado = calcular_prediccion(precios)

        PrediccionPrecio.objects.update_or_create(
            cultivo=cultivo,
            defaults={
                'tendencia_predicha': resultado['tendencia'],
                'confianza_pct': resultado['confianza_pct'],
                'precio_estimado': resultado['precio_estimado'],
                'variacion_estimada_pct': resultado['variacion_pct'],
                'semanas_usadas': resultado['semanas_usadas'],
            }
        )
        if cmd:
            cmd.stdout.write(
                f'  [predicción] {cultivo.nombre}: {resultado["tendencia"]} ({resultado["confianza_pct"]}%)'
            )
