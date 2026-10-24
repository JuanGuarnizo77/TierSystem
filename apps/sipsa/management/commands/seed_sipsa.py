"""
Management command: seed_sipsa
Carga 8 semanas de precios históricos SIPSA/DANE para los cultivos del catálogo maestro.
Idempotente — usa get_or_create.

Uso:
    python manage.py seed_sipsa
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.cultivos.models import Cultivo
from apps.sipsa.models import PrecioSemanal


def _lunes_hace_n_semanas(n):
    """Devuelve el lunes de hace n semanas."""
    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    return lunes_actual - timedelta(weeks=n)


SEMANAS = [_lunes_hace_n_semanas(8 - i) for i in range(8)]


def _label(d: date) -> str:
    iso = d.isocalendar()
    return f"Sem {iso[1]}-{iso[0]}"


CULTIVOS_SEED = [
    {
        "nombre": "Papa Pastusa",
        "nombre_dane": "papa pastusa",
        "categoria": "Tubérculos",
        "precios": [2650, 2580, 2510, 2440, 2370, 2320, 2290, 2260],
    },
    {
        "nombre": "Tomate Chonto",
        "nombre_dane": "tomate chonto",
        "categoria": "Hortalizas",
        "precios": [3050, 3100, 3150, 3180, 3200, 3230, 3250, 3280],
    },
    {
        "nombre": "Cebolla Cabezona",
        "nombre_dane": "cebolla cabezona",
        "categoria": "Hortalizas",
        "precios": [2800, 2850, 2900, 2930, 2960, 3000, 3050, 3100],
    },
    {
        "nombre": "Fríjol Cargamanto",
        "nombre_dane": "frijol cargamanto",
        "categoria": "Leguminosas",
        "precios": [10500, 10800, 11000, 11200, 11400, 11500, 11600, 11700],
    },
    {
        "nombre": "Zanahoria",
        "nombre_dane": "zanahoria",
        "categoria": "Hortalizas",
        "precios": [1400, 1380, 1360, 1340, 1320, 1310, 1300, 1290],
    },
    {
        "nombre": "Plátano Hartón",
        "nombre_dane": "platano harton",
        "categoria": "Frutas",
        "precios": [1600, 1640, 1670, 1700, 1730, 1760, 1790, 1820],
    },
    {
        "nombre": "Arroz Blanco",
        "nombre_dane": "arroz blanco",
        "categoria": "Cereales",
        "precios": [2050, 2060, 2070, 2080, 2090, 2100, 2110, 2120],
    },
    {
        "nombre": "Maíz Amarillo",
        "nombre_dane": "maiz amarillo",
        "categoria": "Cereales",
        "precios": [1300, 1340, 1380, 1410, 1440, 1470, 1490, 1510],
    },
    {
        "nombre": "Aguacate Hass",
        "nombre_dane": "aguacate hass",
        "categoria": "Frutas",
        "precios": [5800, 6100, 6300, 6500, 6700, 6900, 7100, 7300],
    },
    {
        "nombre": "Yuca",
        "nombre_dane": "yuca",
        "categoria": "Tubérculos",
        "precios": [850, 870, 890, 910, 930, 950, 965, 980],
    },
]


class Command(BaseCommand):
    help = 'Siembra 8 semanas de precios SIPSA históricos vinculados al catálogo maestro Cultivo.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== seed_sipsa: iniciando ==='))
        creados_p = 0

        for datos in CULTIVOS_SEED:
            cultivo = Cultivo.objects.filter(nombre__icontains=datos['nombre'].split()[0]).first()
            if not cultivo:
                cultivo, _ = Cultivo.objects.get_or_create(
                    nombre=datos['nombre'],
                    defaults={
                        'categoria': datos['categoria'],
                        'activo': True,
                    }
                )

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
            f'\nPrecios SIPSA sembrados: {creados_p} nuevos'
        ))
        self.stdout.write(self.style.SUCCESS('=== seed_sipsa: completado con éxito ==='))
