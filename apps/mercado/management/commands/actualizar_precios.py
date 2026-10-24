"""
Management command: actualizar_precios
Delega la actualización al comando canónico actualizar_sipsa.

Uso:
    python manage.py actualizar_precios
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Actualiza precios de referencia SIPSA/DANE ejecutando el comando canónico.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== actualizar_precios: delegando a actualizar_sipsa ==='))
        call_command('actualizar_sipsa')
