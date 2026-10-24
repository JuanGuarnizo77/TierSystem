"""
Management command: seed_mercado
Siembra compradores regionales del Huila y los vincula a los cultivos canónicos.

Uso:
    python manage.py seed_mercado
"""
from django.core.management.base import BaseCommand
from apps.mercado.models import Comprador
from apps.mercado.views import DATOS_MERCADO_HUILA
from apps.cultivos.models import Cultivo


class Command(BaseCommand):
    help = 'Siembra compradores regionales del Huila y los vincula a Cultivo.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== seed_mercado: iniciando siembra de compradores ==='))

        compradores_creados = 0
        compradores_existentes = 0

        compradores_map = {}
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
            comp, created = Comprador.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'tipo': datos_c['tipo'],
                    'municipio': datos_c['municipio'],
                    'contacto': datos_c['contacto'],
                    'precio_referencia': datos_c['precio_referencia'],
                    'activo': True,
                }
            )
            # Vincular relacionalmente los cultivos
            for c_nom in datos_c['cultivos']:
                cultivo_obj = Cultivo.objects.filter(nombre__icontains=c_nom).first()
                if cultivo_obj:
                    comp.cultivos_rel.add(cultivo_obj)

            if created:
                compradores_creados += 1
                self.stdout.write(f'  [+] Comprador creado: {nombre}')
            else:
                compradores_existentes += 1
                self.stdout.write(f'  [=] Comprador ya existe: {nombre}')

        # Actualizar contactos específicos
        Comprador.objects.filter(nombre__icontains='CADEFIHUILA').update(
            email='info@cadefihuila.com',
            whatsapp='3105554321',
            sitio_web='https://cadefihuila.com',
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nComprador — creados: {compradores_creados}, existentes: {compradores_existentes}'
            )
        )
