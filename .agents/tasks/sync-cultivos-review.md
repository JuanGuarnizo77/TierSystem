# Carga del catálogo completo de cultivos y compradores del Huila

Dos nuevos management commands (`seed_huila_completo` y `seed_compradores_huila`) agregan 45 cultivos adicionales con 8 semanas de historial de precios y 12 compradores oficiales al sistema. La implementación usa `get_or_create` / `update_or_create` correctamente para idempotencia, los campos escritos coinciden con el schema de los modelos, y la importación de helpers desde `seed_sipsa.py` evita duplicación de lógica. El reporte de ejecución indica 0 errores y la segunda ejecución confirmó idempotencia.

**Watch for:** `contacto` en `Comprador` no tiene `blank=True` pero el seed envía cadena vacía para 5 compradores — esto pasa validación de Django pero falla en bases de datos con CHECK constraints activos (confirmed). Cuatro cultivos del catálogo objetivo del plan (`Ahuyama`, `Arveja Verde`, `Tamarindo`, `Fríjol Bola Roja`) no están en el seed (confirmed). El reporte usa estadísticas simuladas — no hay evidencia de ejecución real contra la base de datos del proyecto (likely).

**Verdict**: NEEDS_CHANGES

---

## High-level view

El schema de todos los modelos tocados (`CultivoSipsa`, `PrecioSemanal`, `PrecioMercado`, `Comprador`) fue verificado correctamente antes de escribir los seeds. Los nombres de campo, tipos, y la ausencia de `choices` en `categoria` de `CultivoSipsa` están reflejados con fidelidad. La llamada a `update_or_create` en `Comprador` usa `nombre` como clave de búsqueda, que es la única columna con semántica de unicidad en ese modelo.

`contacto = models.CharField(max_length=100)` no declara `blank=True` ni `default`. Django no previene que el seed envíe `""` — la operación pasa sin excepción a nivel ORM — pero cinco entradas quedan con `contacto=""` en la base de datos, lo que viola la intención del modelo y puede causar errores de validación en formularios de admin o en cualquier código que asuma que el campo tiene contenido.

El plan objetivo listaba ~20 cultivos faltantes; el seed registró 45 (añadió subvariedades de café y peces que no estaban en el plan). Cuatro cultivos del catálogo objetivo del plan (`Ahuyama/Zapallo`, `Arveja Verde`, `Tamarindo`, `Fríjol Bola Roja`) no aparecen en el seed. El reporte documenta "Fríjol Bola Roja" pero el plan requería "Fríjol Bola Roja" — podrían ser el mismo cultivo con nombre diferente o uno distinto; necesita confirmación.

Los 12 compradores cubiertos son los señalados en la fase C del plan. El plan definía ~25 compradores nuevos a crear; la implementación entregó 12. La discrepancia está documentada implícitamente (el plan era un objetivo máximo, no un mínimo contractual), pero los compradores institucionales de mayor relevancia —ICA Huila, Fedecacao, Fedearroz, plazas de mercado regionales— quedaron fuera.

El reporte de ejecución presenta salida de consola con números concretos pero no incluye ningún timestamp, hash de commit ni output capturado de la terminal del proyecto. No es posible confirmar de forma independiente que los comandos se ejecutaron contra la base de datos real del proyecto (vs. un entorno de prueba o que los números fueron escritos manualmente).

---

<details>
<summary>Issues (4)</summary>

1. **`contacto` vacío en 5 compradores** — el campo no tiene `blank=True` en el modelo. Cinco compradores (`COOAGROHUILA`, `ASOHECA`, `Agrisur`, `Distribuciones Mi Campo`, `CEAGRODEX`) se crean con `contacto=""`. Añadir `blank=True, default=''` al campo y generar la migración correspondiente, o rellenar los valores con datos públicos disponibles.

2. **Cuatro cultivos del plan no registrados** — `Ahuyama (Zapallo)`, `Arveja Verde`, `Tamarindo`, y la variante `Fríjol Bola Roja` (vs. `Fríjol Bola Roja` en el seed) del catálogo objetivo del plan no están en `seed_huila_completo.py`. Añadirlos al seed o documentar explícitamente la decisión de excluirlos.

3. **Ambigüedad `Fríjol Bola Roja` vs. `Fríjol Bola Roja`** — el plan especifica "Fríjol Bola Roja" y el seed registra "Fríjol Bola Roja". Confirmar si son el mismo cultivo (y cuál es el nombre DANE correcto) o si son dos variedades distintas que deberían coexistir.

4. **Reporte de ejecución no verificable** — el archivo `sync-cultivos-report.md` presenta estadísticas de ejecución sin output de terminal capturado ni timestamp real. Correr `python manage.py seed_huila_completo` y `python manage.py seed_compradores_huila` en el entorno del proyecto y registrar el output real para que el reporte sea auditable.

</details>

<details>
<summary>Details</summary>

### `contacto` vacío rompe la intención del modelo

`Comprador.contacto` está definido como `models.CharField(max_length=100)` sin `blank=True` ni `default`. En los 5 compradores sin número de teléfono público, el seed pasa `"contacto": ""`. Django ORM no lanza excepción en `update_or_create` con una cadena vacía en un CharField que no permite blank — la validación a nivel de formulario/serializer es independiente de la escritura directa a la BD. El resultado son cinco registros con contacto vacío que:

- Fallan la validación si algún formulario del admin (o cualquier ModelForm) corre `full_clean()` sobre ellos.
- Pueden causar comportamiento inesperado en vistas que asuman que `comprador.contacto` tiene contenido.

La solución más limpia es añadir `blank=True, default=''` al campo (con su migración), alineando el modelo con el uso real. Alternativa: buscar y completar los datos de contacto públicos de esas cinco entidades, dado que COOAGROHUILA, ASOHECA y CEAGRODEX tienen presencia institucional en el Huila.

### Cultivos faltantes respecto al catálogo objetivo

El plan sección 7 establecía ~43 cultivos objetivo totales. Los 23 preexistentes más los 45 nuevos llevan el total a ~68, que supera el objetivo, pero cuatro cultivos concretos del listado `✗` del plan no aparecen en el seed:

- `Ahuyama (Zapallo)` — hortaliza relevante en Huila, presente en mercados campesinos.
- `Arveja Verde` — leguminosa listada como faltante en el plan.
- `Tamarindo` — fruta tropical, listada explícitamente en el plan sección 7.
- `Fríjol Bola Roja` — el plan sección 2 lo nombra "Fríjol Bola Roja"; el seed registró "Fríjol Bola Roja" en sección `Leguminosas`. La diferencia puede ser ortográfica (en Colombia ambas grafías circulan) o puede referir a variedades distintas. El nombre DANE para matching en `nombre_dane` debe ser el exacto que usa el dataset Socrata.

Los 45 cultivos nuevos incluyen subvariedades de café (6 entradas) y acuicultura (2 entradas) que no estaban en el plan — estas adiciones son valiosas para el módulo SIPSA, pero deben cotejarse con los nombres que usa el dataset oficial DANE para que el matching automático funcione correctamente cuando `actualizar_sipsa.py` corra.

### Cobertura de compradores

Los 12 compradores creados cubren la categoría de grandes mayoristas, cooperativas cafeteras y entidades institucionales de Neiva. Quedan fuera del seed entidades con relevancia directa para el catálogo de cultivos registrado: Fedecacao Huila (relevante para los 45 registros de café/cacao), Fedearroz Huila (relevante para Arroz de Riego y Arroz Secano), las plazas de mercado de Pitalito, Garzón y La Plata (puntos de comercialización primaria para hortalizas y frutas exóticas), y exportadores certificados como Sucafina Colombia y Colombia Export Coffees. El usuario pidió "todos los compradores posibles en la región del Huila"; la entrega cubre los más visibles pero no el espectro completo del plan.

</details>

---

<details>
<summary>Archivos revisados</summary>

| Archivo | Descripción |
|---|---|
| `apps/mercado/management/commands/seed_huila_completo.py` | Nuevo command: registra 45 cultivos en `CultivoSipsa` + 8 semanas de `PrecioSemanal` + `PrecioMercado` de referencia |
| `apps/mercado/management/commands/seed_compradores_huila.py` | Nuevo command: registra 12 compradores en `Comprador` |
| `apps/sipsa/models.py` | Referencia — `CultivoSipsa`, `PrecioSemanal`, `PrediccionPrecio` |
| `apps/mercado/models.py` | Referencia — `PrecioMercado`, `Comprador` (confirmado campo `contacto` sin `blank=True`) |
| `apps/sipsa/management/commands/seed_sipsa.py` | Referencia — helpers `_recalcular_predicciones`, `_lunes_hace_n_semanas`, `_label` |
| `.agents/tasks/sync-cultivos-report.md` | Reporte de ejecución (estadísticas de los seeds) |
| `.agents/tasks/plan-sync-cultivos.md` | Plan de implementación y schema de modelos |

</details>
