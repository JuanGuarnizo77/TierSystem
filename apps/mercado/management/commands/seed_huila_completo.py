"""
Management command: seed_huila_completo
Delega a seed_sipsa para sembrar precios SIPSA en el catálogo maestro Cultivo.

Uso:
    python manage.py seed_huila_completo
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Siembra precios SIPSA en el catálogo maestro Cultivo delegando a seed_sipsa.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== seed_huila_completo: delegando a seed_sipsa ==='))
        call_command('seed_sipsa')
