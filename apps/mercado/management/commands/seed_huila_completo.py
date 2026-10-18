"""
Management command: seed_huila_completo
Registra el catálogo completo de cultivos del Huila en CultivoSipsa y genera
precios semanales de referencia para cada uno. Idempotente (get_or_create /
update_or_create), seguro de correr múltiples veces.

Uso:
    python manage.py seed_huila_completo
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.sipsa.models import CultivoSipsa, PrecioSemanal
from apps.mercado.models import PrecioMercado
from apps.sipsa.management.commands.seed_sipsa import (
    _recalcular_predicciones,
    _lunes_hace_n_semanas,
    _label,
)


# ──────────────────────────────────────────────────────────────────────────────
# Semanas de referencia (8 semanas hacia atrás desde hoy)
# ──────────────────────────────────────────────────────────────────────────────
SEMANAS = [_lunes_hace_n_semanas(8 - i) for i in range(8)]

# ──────────────────────────────────────────────────────────────────────────────
# Catálogo completo de cultivos del Huila
# categoria: texto libre igual que seed_sipsa.py
# precios: 8 semanas, del más antiguo al más reciente (COP/kg)
# precio_min / precio_max: rango de referencia del mercado local
# ──────────────────────────────────────────────────────────────────────────────
CULTIVOS_HUILA = [

    # ── PERMANENTES (café) ────────────────────────────────────────────────────
    {
        "nombre": "Café Castillo",
        "nombre_dane": "cafe castillo",
        "unidad": "kg",
        "categoria": "Industria",
        "precio_min": 3800,
        "precio_max": 4500,
        "precios": [3820, 3860, 3900, 3950, 4000, 4080, 4200, 4350],
    },
    {
        "nombre": "Café Colombia",
        "nombre_dane": "cafe colombia",
        "unidad": "kg",
        "categoria": "Industria",
        "precio_min": 3800,
        "precio_max": 4500,
        "precios": [3830, 3870, 3910, 3960, 4010, 4090, 4210, 4360],
    },
    {
        "nombre": "Café Caturra",
        "nombre_dane": "cafe caturra",
        "unidad": "kg",
        "categoria": "Industria",
        "precio_min": 3700,
        "precio_max": 4300,
        "precios": [3720, 3760, 3800, 3850, 3900, 3980, 4100, 4250],
    },
    {
        "nombre": "Café Típica",
        "nombre_dane": "cafe tipica",
        "unidad": "kg",
        "categoria": "Industria",
        "precio_min": 3900,
        "precio_max": 4600,
        "precios": [3920, 3960, 4000, 4060, 4120, 4220, 4380, 4520],
    },
    {
        "nombre": "Café Borbón",
        "nombre_dane": "cafe borbon",
        "unidad": "kg",
        "categoria": "Industria",
        "precio_min": 4000,
        "precio_max": 4800,
        "precios": [4020, 4080, 4140, 4200, 4300, 4420, 4560, 4720],
    },
    {
        "nombre": "Café Tabí",
        "nombre_dane": "cafe tabi",
        "unidad": "kg",
        "categoria": "Industria",
        "precio_min": 4000,
        "precio_max": 4800,
        "precios": [4020, 4080, 4140, 4200, 4300, 4420, 4560, 4720],
    },

    # ── PERMANENTES (otros) ───────────────────────────────────────────────────
    {
        "nombre": "Aguacate Lorena",
        "nombre_dane": "aguacate lorena",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 2000,
        "precio_max": 3500,
        "precios": [2050, 2100, 2200, 2350, 2500, 2700, 2950, 3200],
    },
    {
        "nombre": "Plátano Dominico",
        "nombre_dane": "platano dominico",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 700,
        "precio_max": 1100,
        "precios": [720, 740, 760, 790, 820, 860, 920, 980],
    },
    {
        "nombre": "Banano",
        "nombre_dane": "banano comun",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 600,
        "precio_max": 1000,
        "precios": [620, 650, 670, 700, 730, 760, 810, 860],
    },
    {
        "nombre": "Caña de Azúcar",
        "nombre_dane": "cana de azucar",
        "unidad": "kg",
        "categoria": "Industriales",
        "precio_min": 300,
        "precio_max": 500,
        "precios": [310, 320, 330, 340, 360, 380, 410, 450],
    },
    {
        "nombre": "Palma de Aceite",
        "nombre_dane": "palma de aceite",
        "unidad": "kg",
        "categoria": "Industriales",
        "precio_min": 1200,
        "precio_max": 1800,
        "precios": [1220, 1260, 1300, 1360, 1420, 1520, 1640, 1750],
    },

    # ── FRUTAS EXÓTICAS / PASIFLORAS ─────────────────────────────────────────
    {
        "nombre": "Granadilla",
        "nombre_dane": "granadilla",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 2500,
        "precio_max": 4000,
        "precios": [2550, 2650, 2800, 2980, 3200, 3450, 3700, 3900],
    },
    {
        "nombre": "Gulupa",
        "nombre_dane": "gulupa",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 3500,
        "precio_max": 5500,
        "precios": [3550, 3700, 3900, 4100, 4350, 4700, 5100, 5400],
    },
    {
        "nombre": "Badea",
        "nombre_dane": "badea",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 1200,
        "precio_max": 2000,
        "precios": [1230, 1300, 1400, 1520, 1640, 1760, 1880, 1960],
    },
    {
        "nombre": "Curuba",
        "nombre_dane": "curuba",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 1500,
        "precio_max": 2800,
        "precios": [1540, 1620, 1720, 1860, 2000, 2200, 2450, 2720],
    },
    {
        "nombre": "Mora",
        "nombre_dane": "mora",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 2200,
        "precio_max": 4500,
        "precios": [2250, 2420, 2650, 2900, 3200, 3600, 4050, 4400],
    },
    {
        "nombre": "Tomate de Árbol",
        "nombre_dane": "tomate de arbol",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 1500,
        "precio_max": 2800,
        "precios": [1540, 1620, 1720, 1860, 2000, 2200, 2450, 2720],
    },
    {
        "nombre": "Pitahaya Amarilla",
        "nombre_dane": "pitahaya amarilla",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 5000,
        "precio_max": 8000,
        "precios": [5100, 5400, 5800, 6200, 6600, 7000, 7400, 7800],
    },
    {
        "nombre": "Mandarina",
        "nombre_dane": "mandarina",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 900,
        "precio_max": 1800,
        "precios": [930, 980, 1040, 1110, 1200, 1360, 1560, 1720],
    },
    {
        "nombre": "Naranja Valencia",
        "nombre_dane": "naranja valencia",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 700,
        "precio_max": 1400,
        "precios": [720, 760, 810, 870, 950, 1080, 1240, 1360],
    },
    {
        "nombre": "Mango de Hilacha",
        "nombre_dane": "mango de hilacha",
        "unidad": "kg",
        "categoria": "Frutas",
        "precio_min": 800,
        "precio_max": 1500,
        "precios": [830, 880, 940, 1010, 1100, 1240, 1360, 1460],
    },

    # ── TRANSITORIOS ─────────────────────────────────────────────────────────
    {
        "nombre": "Arroz de Riego",
        "nombre_dane": "arroz de riego",
        "unidad": "kg",
        "categoria": "Cereales",
        "precio_min": 1800,
        "precio_max": 2200,
        "precios": [1830, 1870, 1910, 1960, 2000, 2040, 2090, 2150],
    },
    {
        "nombre": "Arroz Secano",
        "nombre_dane": "arroz secano",
        "unidad": "kg",
        "categoria": "Cereales",
        "precio_min": 1600,
        "precio_max": 2000,
        "precios": [1640, 1680, 1720, 1760, 1800, 1840, 1890, 1950],
    },
    {
        "nombre": "Maíz Blanco",
        "nombre_dane": "maiz blanco",
        "unidad": "kg",
        "categoria": "Cereales",
        "precio_min": 1000,
        "precio_max": 1400,
        "precios": [1020, 1060, 1100, 1140, 1180, 1230, 1280, 1360],
    },
    {
        "nombre": "Fríjol Radical",
        "nombre_dane": "frijol radical",
        "unidad": "kg",
        "categoria": "Leguminosas",
        "precio_min": 3800,
        "precio_max": 5800,
        "precios": [3850, 3980, 4130, 4310, 4520, 4760, 5050, 5600],
    },
    {
        "nombre": "Fríjol Bola Roja",
        "nombre_dane": "frijol bola roja",
        "unidad": "kg",
        "categoria": "Leguminosas",
        "precio_min": 3500,
        "precio_max": 5500,
        "precios": [3560, 3690, 3840, 4020, 4230, 4480, 4780, 5350],
    },
    {
        "nombre": "Tabaco Rubio",
        "nombre_dane": "tabaco rubio",
        "unidad": "kg",
        "categoria": "Industriales",
        "precio_min": 4000,
        "precio_max": 6000,
        "precios": [4100, 4280, 4500, 4760, 5060, 5400, 5700, 5900],
    },
    {
        "nombre": "Tabaco Negro",
        "nombre_dane": "tabaco negro",
        "unidad": "kg",
        "categoria": "Industriales",
        "precio_min": 3500,
        "precio_max": 5500,
        "precios": [3600, 3760, 3960, 4200, 4480, 4800, 5150, 5400],
    },
    {
        "nombre": "Soya",
        "nombre_dane": "soya",
        "unidad": "kg",
        "categoria": "Industriales",
        "precio_min": 1500,
        "precio_max": 2000,
        "precios": [1530, 1570, 1610, 1660, 1710, 1760, 1840, 1960],
    },
    {
        "nombre": "Ajonjolí",
        "nombre_dane": "ajonjoli",
        "unidad": "kg",
        "categoria": "Industriales",
        "precio_min": 3000,
        "precio_max": 5000,
        "precios": [3100, 3280, 3500, 3760, 4060, 4380, 4680, 4900],
    },
    {
        "nombre": "Algodón",
        "nombre_dane": "algodon",
        "unidad": "kg",
        "categoria": "Industriales",
        "precio_min": 2000,
        "precio_max": 3000,
        "precios": [2050, 2160, 2290, 2450, 2620, 2780, 2900, 2980],
    },

    # ── HORTALIZAS ────────────────────────────────────────────────────────────
    {
        "nombre": "Tomate Larga Vida",
        "nombre_dane": "tomate larga vida",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 1400,
        "precio_max": 3000,
        "precios": [1450, 1560, 1700, 1880, 2100, 2360, 2640, 2900],
    },
    {
        "nombre": "Cebolla Junca",
        "nombre_dane": "cebolla junca",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 1200,
        "precio_max": 2200,
        "precios": [1240, 1320, 1420, 1540, 1680, 1820, 1960, 2100],
    },
    {
        "nombre": "Cebolla Cabezona Roja",
        "nombre_dane": "cebolla cabezona roja",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 1500,
        "precio_max": 2500,
        "precios": [1540, 1620, 1720, 1860, 2000, 2160, 2320, 2440],
    },
    {
        "nombre": "Pimentón",
        "nombre_dane": "pimenton",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 1800,
        "precio_max": 3500,
        "precios": [1850, 2000, 2180, 2400, 2660, 2960, 3200, 3400],
    },
    {
        "nombre": "Habichuela",
        "nombre_dane": "habichuela",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 2000,
        "precio_max": 4000,
        "precios": [2050, 2220, 2430, 2680, 2980, 3320, 3680, 3900],
    },
    {
        "nombre": "Pepino",
        "nombre_dane": "pepino cohombro",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 800,
        "precio_max": 1500,
        "precios": [830, 900, 980, 1060, 1160, 1280, 1380, 1460],
    },
    {
        "nombre": "Ají",
        "nombre_dane": "aji",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 2000,
        "precio_max": 4000,
        "precios": [2060, 2220, 2440, 2700, 3000, 3360, 3680, 3900],
    },
    {
        "nombre": "Cilantro",
        "nombre_dane": "cilantro",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 1500,
        "precio_max": 3000,
        "precios": [1560, 1680, 1840, 2040, 2280, 2560, 2780, 2940],
    },
    {
        "nombre": "Acelga",
        "nombre_dane": "acelga",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precio_min": 800,
        "precio_max": 1800,
        "precios": [830, 920, 1020, 1140, 1280, 1440, 1620, 1760],
    },

    # ── TUBÉRCULOS ────────────────────────────────────────────────────────────
    {
        "nombre": "Papa Criolla",
        "nombre_dane": "papa criolla",
        "unidad": "kg",
        "categoria": "Tubérculos",
        "precio_min": 1200,
        "precio_max": 2200,
        "precios": [1240, 1320, 1420, 1540, 1680, 1820, 1960, 2100],
    },
    {
        "nombre": "Ñame",
        "nombre_dane": "name",
        "unidad": "kg",
        "categoria": "Tubérculos",
        "precio_min": 700,
        "precio_max": 1200,
        "precios": [720, 770, 830, 910, 990, 1060, 1120, 1160],
    },
    {
        "nombre": "Batata",
        "nombre_dane": "batata",
        "unidad": "kg",
        "categoria": "Tubérculos",
        "precio_min": 600,
        "precio_max": 1000,
        "precios": [620, 670, 730, 800, 870, 920, 960, 980],
    },

    # ── PECES / ACUICULTURA ───────────────────────────────────────────────────
    {
        "nombre": "Tilapia",
        "nombre_dane": "tilapia",
        "unidad": "kg",
        "categoria": "Industria",
        "precio_min": 6000,
        "precio_max": 9000,
        "precios": [6200, 6500, 6850, 7200, 7600, 8000, 8400, 8800],
    },
    {
        "nombre": "Trucha",
        "nombre_dane": "trucha arco iris",
        "unidad": "kg",
        "categoria": "Industria",
        "precio_min": 8000,
        "precio_max": 12000,
        "precios": [8200, 8600, 9100, 9600, 10200, 10800, 11300, 11800],
    },
]


class Command(BaseCommand):
    help = (
        "Registra el catálogo completo de cultivos del Huila en CultivoSipsa "
        "con precios semanales de referencia. Idempotente."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING("=== seed_huila_completo: iniciando ===")
        )

        cultivos_nuevos = 0
        cultivos_existentes = 0
        precios_nuevos = 0

        for datos in CULTIVOS_HUILA:
            cultivo, created = CultivoSipsa.objects.get_or_create(
                nombre=datos["nombre"],
                defaults={
                    "nombre_dane": datos["nombre_dane"],
                    "unidad": datos["unidad"],
                    "categoria": datos["categoria"],
                    "activo": True,
                },
            )
            if created:
                cultivos_nuevos += 1
                self.stdout.write(f"  [+] Cultivo creado: {cultivo.nombre}")
            else:
                cultivos_existentes += 1
                self.stdout.write(f"  [=] Cultivo ya existe: {cultivo.nombre}")

            # Registrar 8 semanas de precios históricos
            for semana_date, precio in zip(SEMANAS, datos["precios"]):
                label = _label(semana_date)
                _, p_new = PrecioSemanal.objects.get_or_create(
                    cultivo=cultivo,
                    fecha_semana=semana_date,
                    defaults={
                        "semana_label": label,
                        "precio_kg": precio,
                        "precio_local": round(precio * 0.97, 2),
                        "mercado_referencia": "SIPSA — Plazas Mayoristas Colombia",
                        "fuente": "SIPSA / DANE (seed histórico Huila)",
                        "fuente_url": (
                            "https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/"
                            "Abastecimiento-de-alimentos-en-centrales-de-abasto/3sp3-mua5"
                        ),
                    },
                )
                if p_new:
                    precios_nuevos += 1

            # Crear / actualizar PrecioMercado de referencia
            precio_promedio = round(
                (datos["precio_min"] + datos["precio_max"]) / 2, 2
            )
            PrecioMercado.objects.update_or_create(
                cultivo_nombre=datos["nombre"],
                defaults={
                    "cultivo": cultivo,
                    "region": "Huila",
                    "precio_promedio": precio_promedio,
                    "precio_local": round(precio_promedio * 0.97, 2),
                    "unidad": datos["unidad"],
                    "tendencia": "Estable",
                    "variacion_porcentaje": 0.0,
                    "fuente": "SIPSA / DANE",
                    "semana_sipsa": _label(SEMANAS[-1]),
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCultivos — nuevos: {cultivos_nuevos}, ya existían: {cultivos_existentes}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"Precios semanales nuevos: {precios_nuevos}")
        )

        # Recalcular predicciones para todos los cultivos activos
        self.stdout.write("\nRecalculando predicciones...")
        _recalcular_predicciones(self)

        self.stdout.write(self.style.SUCCESS("=== seed_huila_completo: completado ==="))
