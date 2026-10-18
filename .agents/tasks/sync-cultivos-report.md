# Reporte de Sincronización de Catálogo de Cultivos

Fecha de ejecución: 2026-10-18

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `apps/mercado/migrations/0006_add_cultivo_fk_to_precio_mercado.py` | Nueva migración: agrega FK `PrecioMercado.cultivo → CultivoSipsa` |
| `apps/mercado/migrations/0007_data_normalize_cultivo_nombres.py` | Data migration: renombra nombres legacy, deduplica y enlaza FK |
| `apps/ia_recomendaciones/migrations/0003_alter_cultivoideal_nombre_help_text.py` | Migración: añade `help_text` a `CultivoIdeal.nombre` |
| `apps/mercado/management/commands/seed_mercado.py` | `get_or_create` → `update_or_create`; enlaza FK después de guardar; importa `CultivoSipsa` |
| `apps/mercado/management/commands/actualizar_precios.py` | Importa `CultivoSipsa`; `_guardar_precio` enlaza FK automáticamente |
| `apps/ia_recomendaciones/models.py` | Añade `help_text` y comentario de sincronización a `CultivoIdeal.nombre` |

> Pasos 1 (seed_sipsa), 4 (DATOS_MERCADO_HUILA), 6 (actualizar_precios), 7 (actualizar_sipsa) ya estaban completados en commits anteriores.

## Cultivos añadidos al catálogo (13 nuevos en CultivoSipsa)

| Nombre | nombre_dane | Categoría |
|---|---|---|
| Café | cafe | Industria |
| Cacao | cacao | Industria |
| Aguacate Común | aguacate comun | Frutas |
| Caña Panelera | cana panelera | Industriales |
| Maracuyá | maracuya | Frutas |
| Lulo | lulo | Frutas |
| Cholupa | cholupa | Frutas |
| Sorgo | sorgo | Cereales |
| Limón Tahití | limon tahiti | Frutas |
| Guanábana | guanabana | Frutas |
| Papaya | papaya | Frutas |
| Mango Tommy | mango tommy | Frutas |
| Piña Cayena | pina cayena | Frutas |

## Catálogo canónico final (23 cultivos totales)

```
Tubérculos:     Papa Pastusa, Yuca
Hortalizas:     Tomate Chonto, Cebolla Cabezona, Zanahoria
Leguminosas:    Fríjol Cargamanto
Cereales:       Arroz Blanco, Maíz Amarillo, Sorgo
Frutas:         Aguacate Hass, Aguacate Común, Plátano Hartón,
                Maracuyá, Lulo, Cholupa, Limón Tahití, Guanábana,
                Papaya, Mango Tommy, Piña Cayena
Industriales:   Café, Cacao, Caña Panelera
```

## Normalización de nombres en BD (data migration)

| Nombre legacy eliminado | Nombre canónico |
|---|---|
| Plátano (duplicado) | Plátano Hartón — se eliminó el duplicado renombrado |
| Cacao (pasta) | Eliminado (producto derivado, no cultivo primario) |
| Aguacate Hass (exportación) | Eliminado (canal de venta, no cultivo distinto) |

## Resultado de verificación integral

```
python manage.py check                                    → 0 errores
python manage.py migrate                                  → OK (no migrations to apply)
python manage.py seed_sipsa                               → 13 nuevos cultivos, 104 precios
python manage.py seed_mercado                             → 21 actualizados, 0 nuevos (idempotente)
python manage.py actualizar_sipsa                         → 23 cultivos actualizados
python manage.py actualizar_precios                       → 23 cultivos actualizados

CultivoSipsa.objects.count()                              = 23  ✓ (≥ 23)
PrecioMercado.objects.filter(cultivo__isnull=True).count()= 0   ✓
PrecioMercado con nombres legacy (Maiz, Platano…)         = 0   ✓
```

## Problemas encontrados y cómo se resolvieron

1. **Conflicto de pycache en ia_recomendaciones**: La carpeta `__pycache__` tenía un `.pyc` huérfano de una migración anterior (`0003_alter_cultivoideal_nombre.pyc`), causando que Django detectara dos leaf nodes. Se eliminó el directorio `__pycache__` completo de esa app y el conflicto desapareció.

2. **Duplicado `Plátano Hartón`**: La data migration 0007 renombraba `"Plátano"` → `"Plátano Hartón"`, pero ya existía un registro canónico `"Plátano Hartón"` sembrado en iteraciones anteriores. Se actualizó la data migration para detectar este caso y eliminar el duplicado en vez de renombrar. También se eliminó manualmente el registro ya duplicado en BD antes de correr el seed.

3. **FK nula en registros creados por `actualizar_precios`**: `Cebolla Cabezona` y `Zanahoria` fueron creados por `actualizar_precios` sin FK (el comando no enlazaba FK). Se agregó lógica de enlace FK en `_guardar_precio` y se enlazaron los registros existentes directamente en BD.

## Notas de retrocompatibilidad

- `PrecioMercado.cultivo_nombre` se mantiene intacto en todos los pasos.
- `PrecioMercado.cultivo` (FK) es `null=True, blank=True` — las vistas que no usen la FK siguen funcionando sin cambios.
- `SolicitudAnalisis.cultivo_deseado` (CharField libre) no fue modificado, según las restricciones del plan.
- `CultivoIdeal.nombre` en `ia_recomendaciones` no tiene FK al catálogo; se documentó con `help_text` y comentario en código.
