"""
Management command: seed_mercado
Populates PrecioMercado and Comprador tables from the static DATOS_MERCADO_HUILA dict.
Idempotent — uses get_or_create, safe to run multiple times.

Usage:
    python manage.py seed_mercado
"""
from django.core.management.base import BaseCommand

from apps.mercado.models import PrecioMercado, Comprador
from apps.mercado.views import DATOS_MERCADO_HUILA


class Command(BaseCommand):
    help = 'Seed PrecioMercado and Comprador tables from the static DATOS_MERCADO_HUILA reference data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== seed_mercado: iniciando siembra de datos ==='))

        precios_creados = 0
        precios_existentes = 0

        for cultivo_nombre, datos in DATOS_MERCADO_HUILA.items():
            # Parse variation string like "+8%" or "-5%" into float
            variacion_str = datos.get('variacion', '0%').replace('%', '').replace('+', '')
            try:
                variacion_float = float(variacion_str)
            except ValueError:
                variacion_float = 0.0

            pm, created = PrecioMercado.objects.get_or_create(
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
            if created:
                precios_creados += 1
                self.stdout.write(f'  [+] PrecioMercado creado: {cultivo_nombre}')
            else:
                precios_existentes += 1
                self.stdout.write(f'  [=] PrecioMercado ya existe: {cultivo_nombre}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPrecioMercado — creados: {precios_creados}, ya existían: {precios_existentes}'
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
