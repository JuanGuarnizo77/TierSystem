"""
Comando de Gestión Django: `poblar_cultivos_completo`.
======================================================
Invoca programáticamente el semillero maestro `seed_cultivos.py` para asegurar
que la base de datos MySQL cuente con todos los cultivos agroclimáticos del Huila,
sus rangos óptimos de N-P-K, pH, humedad, temperatura, conductividad y pisos altitudinales.
"""

from django.core.management.base import BaseCommand
import seed_cultivos


class Command(BaseCommand):
    """Ejecuta el semillero de cultivos oficiales para inicializar el catálogo de TierSystem."""
    help = "Puebla el catálogo maestro Cultivo delegando al script canónico seed_cultivos."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== poblar_cultivos_completo: ejecutando seed_cultivos ==="))
        seed_cultivos.run()
        self.stdout.write(self.style.SUCCESS("=== Catálogo sincronizado exitosamente ==="))
