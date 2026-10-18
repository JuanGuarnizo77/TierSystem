# Reporte: Barras de búsqueda en módulos con cultivos

## Vistas modificadas

Ninguna vista (`views.py`) fue modificada. Toda la búsqueda es **client-side** (JS), como indica el plan, ya que los conjuntos de datos son pequeños (máximo ~40 cultivos).

## Templates modificados

| Template | Cambio |
|----------|--------|
| `templates/sipsa/dashboard.html` | Añadida barra `id="buscarCultivoSipsa"` + `data-nombre`/`data-categoria` en cada `<tr>` + fila "sin resultados" + JS de filtrado en `{% block extra_js %}` |
| `templates/agricultor/precios_sipsa.html` | Añadida barra `id="buscarPrecioSipsa"` + `data-cultivo` en cada `<tr>` principal + fila "sin resultados" + JS que oculta también la fila de detalle expandible (slugified) |
| `templates/agricultor/historial.html` | Añadida barra `id="buscarHistorial"` (solo visible cuando hay solicitudes) + `data-terreno`/`data-cultivo` en cada card + div "sin resultados" + JS en `{% block extra_js %}` |
| `templates/laboratorista/historial.html` | Añadida barra `id="buscarHistorialLab"` + `data-search` (terreno + cultivo + agricultor) en cada `<tr>` + fila "sin resultados" colspan=7 + JS que no interfiere con checkboxes de comparación |
| `templates/agricultor/mi_tienda.html` | Añadida barra `id="buscarMiTienda"` + `data-nombre` en cada card de producto + div "sin resultados" + JS en `{% block extra_js %}` |

## Templates NO modificados (ya tenían búsqueda funcional)

| Template | Razón |
|----------|-------|
| `templates/agricultor/cultivos.html` | Ya tiene `id="searchInput"` con `applyFilters()` completo |
| `templates/agricultor/mercado.html` | Ya tiene `id="buscarProducto"` con JS funcional |
| `templates/admin/cultivos.html` | Ya tiene `id="buscarCultivo"` con filtrado sobre `.cultivo-card` |

## Resultado de `python manage.py check`

```
System check identified no issues (0 silenced).
```

## Resultado de validación de templates

```
OK: sipsa/dashboard.html
OK: agricultor/precios_sipsa.html
OK: agricultor/historial.html
OK: laboratorista/historial.html
OK: agricultor/mi_tienda.html
```

## Notas

- La búsqueda es case-insensitive (todo comparado en lowercase vía filtros Django `|lower` y `.toLowerCase()` en JS).
- Los filtros y funciones existentes (`toggleDetalle`, `actualizarSeleccionComparar`, `verReporte`, etc.) no fueron modificados.
- El JS de búsqueda del laboratorista usa `data-search` únicamente; no toca los atributos `data-id` de los checkboxes.
- La barra de historial agricultor solo se renderiza cuando hay solicitudes (condición `{% if solicitudes %}`), evitando un widget vacío en la vista vacía.
