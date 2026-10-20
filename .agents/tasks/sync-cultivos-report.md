# sync-cultivos: Mercado SIPSA ↔ Reportes SIPSA/DANE

**Status:** ✅ Complete  
**Date:** 2025-01-31

## What changed

### `apps/mercado/views.py`
- Added imports: `CultivoSipsa`, `PrecioSemanal`, `PrediccionPrecio` from `apps.sipsa.models`; `date` from `datetime`.
- Added module-level `TENDENCIA_MAP` constant for normalising tendency strings from both modules.
- Added helper `_construir_historial_sipsa(cultivo)` — builds readable date-range price history from `PrecioSemanal` rows.
- Added helper `_obtener_compradores_sipsa(cultivo)` — fetches buyers from `Comprador` DB by cultivo name, falling back to the static `DATOS_MERCADO_HUILA` dict.
- Replaced `cultivos_disponibles` block: now reads from `CultivoSipsa.objects.filter(activo=True)` instead of merging `PrecioMercado` names with the static dict.
- Replaced the `precios_tabla` building loop: now iterates over `CultivoSipsa.objects.filter(activo=True).order_by('nombre')` so Mercado SIPSA and Reportes SIPSA/DANE share the same catalogue. Price source priority: `PrecioSemanal` → `PrecioMercado` (FK then name) → static dict. Prediction source priority: `PrediccionPrecio` (via `cultivo.prediccion`) → `PrecioMercado.tendencia` → static dict. Each row now also carries `confianza` and `detalle_prediccion` fields.

### `templates/agricultor/precios_sipsa.html`
- Added **Confianza** column header (`<th>`) between Tendencia and Variación %.
- Added **Confianza** data cell (`<td>`) in each table row showing the prediction confidence badge (blue pill) or `—` if none.
- Updated all three `colspan="8"` → `colspan="9"` (expandable detail row, empty state row, no-search-results row).
- Added **Predicción SIPSA** expandable section inside the per-row detail panel, shown only when `item.detalle_prediccion` is non-empty.

## Verification
- `python -m py_compile apps/mercado/views.py` → no errors
- `python manage.py check` → 0 issues
- `None` predictions handled gracefully via `try/except` on `cultivo.prediccion` accessor and conditional fallback chain.

## No migrations needed
The FK `PrecioMercado.cultivo → CultivoSipsa` already existed in the schema.
