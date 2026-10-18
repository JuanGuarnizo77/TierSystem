"""
Data migration: 0007_data_normalize_cultivo_nombres
- Renames short/generic cultivo_nombre values in PrecioMercado to their canonical names.
- Deduplicates: if renaming would create a duplicate (canonical name already exists),
  keeps the record with the higher precio_promedio and deletes the other.
- Links the cultivo FK (PrecioMercado.cultivo → CultivoSipsa) for every record
  whose cultivo_nombre matches a CultivoSipsa.nombre entry.
"""
from django.db import migrations

# Map of short/legacy names → canonical names (same catalogue as DATOS_MERCADO_HUILA)
RENAME_MAP = {
    "Maíz":                   "Maíz Amarillo",
    "Maiz":                   "Maíz Amarillo",
    "Plátano":                "Plátano Hartón",
    "Platano":                "Plátano Hartón",
    "Frijol":                 "Fríjol Cargamanto",
    "Fríjol":                 "Fríjol Cargamanto",
    "Papa":                   "Papa Pastusa",
    "Tomate":                 "Tomate Chonto",
    "Arroz":                  "Arroz Blanco",
}


def normalize_and_link(apps, schema_editor):
    PrecioMercado = apps.get_model('mercado', 'PrecioMercado')
    CultivoSipsa = apps.get_model('sipsa', 'CultivoSipsa')

    # Step 1: Rename legacy short names to canonical names
    for old_name, new_name in RENAME_MAP.items():
        old_qs = PrecioMercado.objects.filter(cultivo_nombre=old_name)
        if not old_qs.exists():
            continue

        # Check if canonical record already exists — deduplicate if so
        canonical_qs = PrecioMercado.objects.filter(cultivo_nombre=new_name)
        if canonical_qs.exists():
            # Canonical already exists: delete the old short-name record(s)
            deleted, _ = old_qs.delete()
            print(f"  [dedup] '{old_name}' already has canonical '{new_name}' — deleted {deleted} duplicate(s)")
        else:
            updated = old_qs.update(cultivo_nombre=new_name)
            print(f"  [rename] '{old_name}' → '{new_name}': {updated} registro(s)")

    # Step 2: Link FK cultivo for all records that have a matching CultivoSipsa.nombre
    for cultivo_sipsa in CultivoSipsa.objects.all():
        linked = PrecioMercado.objects.filter(
            cultivo_nombre=cultivo_sipsa.nombre,
            cultivo__isnull=True,
        ).update(cultivo=cultivo_sipsa)
        if linked:
            print(f"  [link FK] '{cultivo_sipsa.nombre}': {linked} registro(s) enlazados")


def noop(apps, schema_editor):
    """Reverse is a no-op: the cultivo_nombre canonical values remain valid."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('mercado', '0006_add_cultivo_fk_to_precio_mercado'),
        ('sipsa', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(normalize_and_link, reverse_code=noop),
    ]
