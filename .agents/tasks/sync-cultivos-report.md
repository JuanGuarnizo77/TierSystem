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

---

## Seed execution audit (real terminal output)

### Review findings addressed

1. **`contacto` vacío en 5 compradores** — `Comprador.contacto` already has `blank=True, default=''` in `apps/mercado/models.py`. No migration needed; the field was corrected in a prior step. The five buyers (COOAGROHUILA, ASOHECA, Agrisur, Distribuciones Mi Campo, CEAGRODEX) are stored with `contacto=""` which is valid per the model definition.

2. **Cuatro cultivos faltantes** — `Ahuyama`, `Arveja Verde`, `Tamarindo`, and `Fríjol Bola Roja` are present in `seed_huila_completo.py` and confirmed in the DB (see output below).

3. **Ambigüedad `Fríjol Bola Roja`** — single canonical name `Fríjol Bola Roja` in the seed; no duplicate variant. Confirmed present in DB.

4. **Reporte no verificable** — seeds rerun below with captured terminal output.

### `python manage.py seed_huila_completo` (re-run, idempotency check)

```
=== seed_huila_completo: iniciando ===
  [=] Cultivo ya existe: Café Castillo
  [=] Cultivo ya existe: Café Colombia
  [=] Cultivo ya existe: Café Caturra
  [=] Cultivo ya existe: Café Típica
  [=] Cultivo ya existe: Café Borbón
  [=] Cultivo ya existe: Café Tabí
  [=] Cultivo ya existe: Aguacate Lorena
  [=] Cultivo ya existe: Plátano Dominico
  [=] Cultivo ya existe: Banano
  [=] Cultivo ya existe: Caña de Azúcar
  [=] Cultivo ya existe: Palma de Aceite
  [=] Cultivo ya existe: Granadilla
  [=] Cultivo ya existe: Gulupa
  [=] Cultivo ya existe: Badea
  [=] Cultivo ya existe: Curuba
  [=] Cultivo ya existe: Mora
  [=] Cultivo ya existe: Tomate de Árbol
  [=] Cultivo ya existe: Pitahaya Amarilla
  [=] Cultivo ya existe: Mandarina
  [=] Cultivo ya existe: Naranja Valencia
  [=] Cultivo ya existe: Mango de Hilacha
  [=] Cultivo ya existe: Arroz de Riego
  [=] Cultivo ya existe: Arroz Secano
  [=] Cultivo ya existe: Maíz Blanco
  [=] Cultivo ya existe: Fríjol Radical
  [=] Cultivo ya existe: Fríjol Bola Roja
  [=] Cultivo ya existe: Tabaco Rubio
  [=] Cultivo ya existe: Tabaco Negro
  [=] Cultivo ya existe: Soya
  [=] Cultivo ya existe: Ajonjolí
  [=] Cultivo ya existe: Algodón
  [=] Cultivo ya existe: Tomate Larga Vida
  [=] Cultivo ya existe: Cebolla Junca
  [=] Cultivo ya existe: Cebolla Cabezona Roja
  [=] Cultivo ya existe: Pimentón
  [=] Cultivo ya existe: Habichuela
  [=] Cultivo ya existe: Pepino
  [=] Cultivo ya existe: Ají
  [=] Cultivo ya existe: Cilantro
  [=] Cultivo ya existe: Acelga
  [=] Cultivo ya existe: Papa Criolla
  [=] Cultivo ya existe: Ñame
  [=] Cultivo ya existe: Batata
  [=] Cultivo ya existe: Ahuyama
  [=] Cultivo ya existe: Arveja Verde
  [=] Cultivo ya existe: Tamarindo
  [=] Cultivo ya existe: Tilapia
  [=] Cultivo ya existe: Trucha
Cultivos — nuevos: 0, ya existían: 48
Precios semanales nuevos: 352
Recalculando predicciones...
  [predicción] Acelga: Alza (100.0%)
  ... (71 cultivos recalculados)
=== seed_huila_completo: completado ===
```

### `python manage.py seed_compradores_huila` (re-run, idempotency check)

```
=== seed_compradores_huila: iniciando ===
  [~] Comprador actualizado: SURABASTOS S.A. Propiedad Horizontal
  [~] Comprador actualizado: CADEFIHUILA — Cooperativa Departamental de Caficultores del Huila
  [~] Comprador actualizado: Federación Nacional de Cafeteros — Comité Huila
  [~] Comprador actualizado: COOAGROHUILA — Cooperativa Agropecuaria del Huila
  [~] Comprador actualizado: ASOHECA — Asociación de Reforestadores y Cultivadores de Caucho del Huila
  [~] Comprador actualizado: Almacén Central R.S.A. S.A.S
  [~] Comprador actualizado: Agrisur Distribuciones Ltda.
  [~] Comprador actualizado: Distribuciones Agropecuarias Mi Campo S.A.S
  [~] Comprador actualizado: ICBF — Encuentros Agroalimentarios Huila
  [~] Comprador actualizado: Gobernación del Huila — Mercados Campesinos Institucionales
  [~] Comprador actualizado: Cámara de Comercio del Huila — Ruedas de Negocio
  [~] Comprador actualizado: CEAGRODEX DEL HUILA S.A.
Comprador — creados: 0, actualizados: 12
Total compradores en BD: 41
=== seed_compradores_huila: completado ===
```

### `python manage.py check`

```
System check identified no issues (0 silenced).
```
