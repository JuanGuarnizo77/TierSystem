"""
Management command: poblar_cultivos_completo
Delega el poblado de cultivos al script canonical seed_cultivos.
"""
from django.core.management.base import BaseCommand
import seed_cultivos


class Command(BaseCommand):
    help = "Puebla el catálogo maestro Cultivo delegando a seed_cultivos."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== poblar_cultivos_completo: ejecutando seed_cultivos ==="))
        seed_cultivos.run()
        self.stdout.write(self.style.SUCCESS("=== Catálogo sincronizado exitosamente ==="))
