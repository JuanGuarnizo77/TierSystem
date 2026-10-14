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

def _lunes_hace_n_semanas(n):
    """Devuelve el lunes de hace n semanas."""
    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    return lunes_actual - timedelta(weeks=n)


# Generar 8 semanas desde hace 8 semanas hasta la semana pasada
SEMANAS = [_lunes_hace_n_semanas(8 - i) for i in range(8)]


def _label(d: date) -> str:
    iso = d.isocalendar()
    return f"Sem {iso[1]}-{iso[0]}"


CULTIVOS_SEED = [
    {
        "nombre": "Papa Pastusa",
        "nombre_dane": "papa pastusa",
        "unidad": "kg",
        "categoria": "Tubérculos",
        # precios semanas 1..8 (descendente — tendencia Baja)
        "precios": [2650, 2580, 2510, 2440, 2370, 2320, 2290, 2260],
    },
    {
        "nombre": "Tomate Chonto",
        "nombre_dane": "tomate chonto",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precios": [3050, 3100, 3150, 3180, 3200, 3230, 3250, 3280],
    },
    {
        "nombre": "Cebolla Cabezona",
        "nombre_dane": "cebolla cabezona",
        "unidad": "kg",
        "categoria": "Hortalizas",
        "precios": [2800, 2850, 2900, 2930, 2960, 3000, 3050, 3100],
    },
    {
        "nombre": "Fríjol Cargamanto",
        "nombre_dane": "frijol cargamanto",
        "unidad": "kg",
        "categoria": "Leguminosas",
        "precios": [10500, 10800, 11000, 11200, 11400, 11500, 11600, 11700],
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
        "precios": [1600, 1640, 1670, 1700, 1730, 1760, 1790, 1820],
    },
    {
        "nombre": "Arroz Blanco",
        "nombre_dane": "arroz blanco",
        "unidad": "kg",
        "categoria": "Cereales",
        "precios": [2050, 2060, 2070, 2080, 2090, 2100, 2110, 2120],
    },
    {
        "nombre": "Maíz Amarillo",
        "nombre_dane": "maiz amarillo",
        "unidad": "kg",
        "categoria": "Cereales",
        "precios": [1300, 1340, 1380, 1410, 1440, 1470, 1490, 1510],
    },
    {
        "nombre": "Aguacate Hass",
        "nombre_dane": "aguacate hass",
        "unidad": "kg",
        "categoria": "Frutas",
        "precios": [5800, 6100, 6300, 6500, 6700, 6900, 7100, 7300],
    },
    {
        "nombre": "Yuca",
        "nombre_dane": "yuca",
        "unidad": "kg",
        "categoria": "Tubérculos",
        "precios": [850, 870, 890, 910, 930, 950, 965, 980],
    },
]


class Command(BaseCommand):
    help = 'Siembra 8 semanas de precios SIPSA históricos para 10 cultivos.'

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
                ps, p_new = PrecioSemanal.objects.get_or_create(
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
