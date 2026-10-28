"""
Comando de Gestión Django: `seed_sipsa_completo`.
==================================================
Genera 8 semanas de precios semanales (`PrecioSemanal`) para los 49 cultivos
nuevos que fueron insertados por `seed_cultivos_completo`.

Es idempotente: usa `get_or_create` con clave (cultivo, fecha_semana). Puede
ejecutarse múltiples veces sin duplicar registros.

Uso:
    python manage.py seed_sipsa_completo
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.cultivos.models import Cultivo
from apps.sipsa.models import PrecioSemanal


def _lunes_hace_n_semanas(n):
    """Calcula la fecha del lunes correspondiente a `n` semanas atrás."""
    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    return lunes_actual - timedelta(weeks=n)


# Las 8 semanas históricas previas (de más antigua a más reciente)
SEMANAS = [_lunes_hace_n_semanas(8 - i) for i in range(8)]


def _label(d: date) -> str:
    """Retorna etiqueta en formato 'Sem N-AAAA'."""
    iso = d.isocalendar()
    return f"Sem {iso[1]}-{iso[0]}"


# Tabla de precios base por cultivo (COP/kg). Los precios aumentan ligeramente
# semana a semana (±3–5 %) para reflejar variación de mercado regional.
PRECIOS_REFERENCIA = [
    {"nombre": "Plátano",          "precio_ref": 1600},
    {"nombre": "Pitahaya Roja",    "precio_ref": 8000},
    {"nombre": "Uchuva",           "precio_ref": 4500},
    {"nombre": "Sandía",           "precio_ref": 900},
    {"nombre": "Melón",            "precio_ref": 1200},
    {"nombre": "Guayaba",          "precio_ref": 1800},
    {"nombre": "Breva",            "precio_ref": 3500},
    {"nombre": "Borojó",           "precio_ref": 3000},
    {"nombre": "Marañón",          "precio_ref": 2500},
    {"nombre": "Carambolo",        "precio_ref": 2200},
    {"nombre": "Maíz Tradicional", "precio_ref": 1200},
    {"nombre": "Maíz Híbrido",     "precio_ref": 1350},
    {"nombre": "Arroz Riego",      "precio_ref": 2000},
    {"nombre": "Trigo",            "precio_ref": 1800},
    {"nombre": "Papa",             "precio_ref": 2200},
    {"nombre": "Arracacha",        "precio_ref": 1500},
    {"nombre": "Bore",             "precio_ref": 800},
    {"nombre": "Remolacha",        "precio_ref": 1200},
    {"nombre": "Frijol Cargamanto","precio_ref": 11000},
    {"nombre": "Frijol Voluble",   "precio_ref": 9000},
    {"nombre": "Arveja",           "precio_ref": 4500},
    {"nombre": "Maní",             "precio_ref": 3200},
    {"nombre": "Garbanzo",         "precio_ref": 5000},
    {"nombre": "Tomate de Mesa",   "precio_ref": 3200},
    {"nombre": "Cebolla Larga",    "precio_ref": 2800},
    {"nombre": "Repollo",          "precio_ref": 1100},
    {"nombre": "Lechuga",          "precio_ref": 1500},
    {"nombre": "Pepino Cohombro",  "precio_ref": 1400},
    {"nombre": "Espinaca",         "precio_ref": 2500},
    {"nombre": "Brócoli",          "precio_ref": 2800},
    {"nombre": "Coliflor",         "precio_ref": 2600},
    {"nombre": "Apio",             "precio_ref": 2000},
    {"nombre": "Berenjena",        "precio_ref": 1800},
    {"nombre": "Rábano",           "precio_ref": 1000},
    {"nombre": "Calabacín",        "precio_ref": 1300},
    {"nombre": "Tabaco",           "precio_ref": 3500},
    {"nombre": "Palma Africana",   "precio_ref": 950},
    {"nombre": "Caucho",           "precio_ref": 2800},
    {"nombre": "Sacha Inchi",      "precio_ref": 4500},
    {"nombre": "Stevia",           "precio_ref": 8000},
    {"nombre": "Heliconias",       "precio_ref": 2500},
    {"nombre": "Anturios",         "precio_ref": 3500},
    {"nombre": "Albahaca",         "precio_ref": 3000},
    {"nombre": "Menta",            "precio_ref": 3500},
    {"nombre": "Tomillo",          "precio_ref": 4000},
    {"nombre": "Hierbabuena",      "precio_ref": 3000},
    {"nombre": "Orégano",          "precio_ref": 4500},
    {"nombre": "Jengibre",         "precio_ref": 5000},
    {"nombre": "Cúrcuma",          "precio_ref": 4500},
]

# Factores de variación semanal (semana 1 = hace 8 semanas, semana 8 = actual)
# Cada factor se aplica al precio_ref para generar la serie temporal.
FACTORES = [0.88, 0.90, 0.92, 0.94, 0.96, 0.97, 0.99, 1.00]


class Command(BaseCommand):
    """Siembra 8 semanas de precios SIPSA para los 49 nuevos cultivos (idempotente)."""
    help = 'Siembra 8 semanas de precios SIPSA para los 49 cultivos nuevos.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== seed_sipsa_completo: iniciando ==='))
        creados = 0
        omitidos = 0

        for entrada in PRECIOS_REFERENCIA:
            nombre = entrada['nombre']
            precio_ref = entrada['precio_ref']

            # Resolver el cultivo en BD
            cultivo = Cultivo.objects.filter(nombre=nombre).first()
            if not cultivo:
                self.stdout.write(self.style.WARNING(
                    f'  [SKIP] Cultivo no encontrado en BD: {nombre}'
                ))
                omitidos += 1
                continue

            # Generar 8 semanas de precios
            for semana_date, factor in zip(SEMANAS, FACTORES):
                precio_kg = round(precio_ref * factor, 2)
                precio_local = round(precio_kg * 0.97, 2)
                label = _label(semana_date)

                _, nuevo = PrecioSemanal.objects.get_or_create(
                    cultivo=cultivo,
                    fecha_semana=semana_date,
                    defaults={
                        'semana_label': label,
                        'precio_kg': precio_kg,
                        'precio_local': precio_local,
                        'mercado_referencia': 'SIPSA — Plazas Mayoristas Colombia',
                        'fuente': 'SIPSA / DANE (seed histórico completo)',
                        'fuente_url': (
                            'https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/'
                            'Abastecimiento-de-alimentos-en-centrales-de-abasto/3sp3-mua5'
                        ),
                    }
                )
                if nuevo:
                    creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nPrecios SIPSA creados: {creados} | Cultivos omitidos (no en BD): {omitidos}'
        ))
        self.stdout.write(self.style.SUCCESS('=== seed_sipsa_completo: completado ==='))
