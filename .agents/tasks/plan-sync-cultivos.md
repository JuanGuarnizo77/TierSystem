# Plan de Sincronización: Cultivos y Compradores del Huila

Fecha de investigación: 2025-01

---

## 1. Schema exacto de cada modelo relevante

### `apps/sipsa/models.py` — `CultivoSipsa` (catálogo maestro)
```
nombre          CharField(max_length=120, unique=True)          REQUERIDO
nombre_dane     CharField(max_length=120, blank=True)           opcional
unidad          CharField(max_length=50, default='kg')          opcional
categoria       CharField(max_length=80, blank=True)            opcional — texto libre
activo          BooleanField(default=True)
fecha_creacion  DateTimeField(auto_now_add=True)
```
- Sin choices en `categoria` — texto libre (Tubérculos, Frutas, Hortalizas, Cereales, Leguminosas, Industriales, Industria)
- Campos obligatorios en código: solo `nombre` (el resto tiene defaults)

### `apps/sipsa/models.py` — `PrecioSemanal`
```
cultivo         FK(CultivoSipsa, CASCADE)                       REQUERIDO
fecha_semana    DateField                                        REQUERIDO
semana_label    CharField(max_length=30)                        REQUERIDO
precio_kg       DecimalField(max_digits=12, decimal_places=2)   REQUERIDO
precio_local    DecimalField(null=True, blank=True)             opcional
mercado_referencia CharField(max_length=200, default='SIPSA — Plazas Mayoristas Colombia')
fuente          CharField(max_length=300, default='SIPSA / DANE')
fuente_url      CharField(max_length=500, blank=True, default='')
fecha_registro  DateTimeField(auto_now_add=True)
unique_together: (cultivo, fecha_semana)
```

### `apps/sipsa/models.py` — `PrediccionPrecio`
```
cultivo             OneToOneField(CultivoSipsa)                 REQUERIDO
tendencia_predicha  CharField(choices=['Alza','Baja','Estable']) REQUERIDO
confianza_pct       FloatField(default=0.0)
precio_estimado     DecimalField(null=True, blank=True)
variacion_estimada_pct FloatField(default=0.0)
semanas_usadas      IntegerField(default=0)
fecha_calculo       DateTimeField(auto_now=True)
```

### `apps/mercado/models.py` — `PrecioMercado`
```
cultivo_nombre      CharField(max_length=100)                   REQUERIDO (clave de búsqueda)
cultivo             FK('sipsa.CultivoSipsa', null=True, blank=True) opcional (FK al catálogo)
region              CharField(max_length=100, default='Huila')
precio_promedio     DecimalField(max_digits=12, decimal_places=2) REQUERIDO
precio_local        DecimalField(null=True, blank=True)
unidad              CharField(max_length=30, default='kg')
tendencia           CharField(choices=['Alza','Baja','Estable'])
variacion_porcentaje FloatField(default=0.0)
fuente              CharField(max_length=200, default='SIPSA / DANE')
semana_sipsa        CharField(blank=True, default='')
fuente_url          CharField(max_length=500, blank=True, default='')
ultima_actualizacion DateTimeField(auto_now=True)
```

### `apps/mercado/models.py` — `Comprador`
```
nombre              CharField(max_length=150)                   REQUERIDO
tipo                CharField(max_length=50)                    REQUERIDO (texto libre, no choices)
municipio           CharField(max_length=100, default='Neiva, Huila')
contacto            CharField(max_length=100)                   REQUERIDO
cultivos_interes    TextField                                    REQUERIDO (separados por comas)
precio_referencia   CharField(null=True, blank=True)
activo              BooleanField(default=True)
email               EmailField(blank=True, default='')
whatsapp            CharField(max_length=20, blank=True, default='')
sitio_web           CharField(max_length=200, blank=True, default='')
```
- **SIN relación M2M con cultivos** — usa `cultivos_interes` como TextField de texto libre
- **SIN campo `descripcion`** — no existe en el modelo actual
- Campos `email`, `whatsapp`, `sitio_web` YA EXISTEN (añadidos en FEAT-001)

---

## 2. Cultivos actualmente registrados en BD

Total: **23 cultivos** en `CultivoSipsa`

```
Aguacate Común      (Frutas)
Aguacate Hass       (Frutas)
Arroz Blanco        (Cereales)
Cacao               (Industria)
Café                (Industria)
Caña Panelera       (Industriales)
Cebolla Cabezona    (Hortalizas)
Cholupa             (Frutas)
Fríjol Cargamanto   (Leguminosas)
Guanábana           (Frutas)
Limón Tahití        (Frutas)
Lulo                (Frutas)
Mango Tommy         (Frutas)
Maracuyá            (Frutas)
Maíz Amarillo       (Cereales)
Papa Pastusa        (Tubérculos)
Papaya              (Frutas)
Piña Cayena         (Frutas)
Plátano Hartón      (Frutas)
Sorgo               (Cereales)
Tomate Chonto       (Hortalizas)
Yuca                (Tubérculos)
Zanahoria           (Hortalizas)
```

**Cultivos del Huila aún NO registrados** (objetivo del usuario: "todos los posibles"):
```
# Tubérculos / Raíces
Ñame
Batata (Camote)

# Hortalizas
Pimentón
Pepino Cohombro
Ahuyama (Zapallo)
Habichuela

# Leguminosas
Fríjol Bola Roja
Fríjol Radical
Arveja Verde

# Cereales / Granos
Maíz Blanco

# Frutas
Granadilla
Badea
Banano Común
Mandarina
Naranja Valencia
Tamarindo
Gulupa

# Industriales / Especiales
Soya
Tabaco
Achiote (Bija)
Stevia
```

---

## 3. Compradores actualmente registrados

Total: **29 compradores** en BD. La mayoría tienen `email`, `whatsapp` y `sitio_web` vacíos.

Solo tienen contacto digital completo:
- `CADEFIHUILA - Cooperativa Departamental`: email, whatsapp, sitio_web ✓
- `Central de Abastos Surabastos` / `Surabastos Cacao Neiva`: email, whatsapp, sitio_web ✓

Los 27 restantes tienen esos campos vacíos.

**Compradores oficiales del Huila aún NO registrados** (entidades reales):
```
# Institucionales / Gubernamentales
Secretaría de Agricultura y Minería del Huila (Gobernación)
Alcaldía de Neiva — Programa de Abastecimiento
ICA Regional Huila
MADR — Ministerio de Agricultura (oficina Huila)
FINAGRO (oficina Huila)
Banco Agrario — Sucursal Neiva

# Plazas y Centrales
Plaza de Mercado El Emporio (Garzón)
Plaza de Mercado La 21 (Neiva)
Plaza de Mercado de Pitalito
Galería Las Palmas (Campoalegre)
Plaza de Mercado de La Plata
Plaza de Mercado Rivera

# Cooperativas y Asociaciones
COAGROFRUVER (Cooperativa Frutas y Verduras Huila)
ASOHOCOL (Asociación Hortofrutícola Colombia — Huila)
ASOHOFRUCOL Huila (ya registrada)
Cooperativa San Isidro (Isnos, Huila)
APROCAM (Asociación Productores Campoalegre)

# Agroindustria y Transformadores
Postobón S.A. — Planta Neiva (jugos tropicales)
Bavaria S.A. — compra maíz/sorgo región
Harinera del Valle — compra trigo/maíz Huila
Indupanela (Asociación Paneleros Huila)

# Exportadores certificados
Sucafina Colombia S.A. (exportador café)
Trilladora Cristancho (Neiva — café y cacao)
Colombia Export Coffees S.A.S. (Pitalito)
```

---

## 4. Campos faltantes en `Comprador`

El modelo `Comprador` **tiene todos los campos necesarios**:
- `tipo` ✅ (ya existe)
- `sitio_web` ✅ (ya existe)
- `email` ✅ (ya existe)
- `whatsapp` ✅ (ya existe)
- `descripcion` ❌ **NO existe** — el usuario no lo requirió explícitamente, pero sería útil para compradores institucionales

**Decisión**: No se añade `descripcion` al modelo porque el usuario no lo solicitó y hacerlo requeriría una migración. Los datos de descripción pueden ir en `cultivos_interes` extendido o en el campo `tipo`. Se puede añadir en una iteración posterior si se necesita.

**Decisión sobre M2M cultivos**: NO se implementa M2M entre `Comprador` y `CultivoSipsa`. El campo `cultivos_interes` como TextField es suficiente para la funcionalidad actual (búsqueda con `icontains`) y no requiere migración de esquema.

---

## 5. Estrategia de implementación — decisiones

### Estrategia elegida: Nuevo management command `seed_huila_completo.py`

**Por qué no modificar los existentes:**
- `seed_sipsa.py`: ya funciona correctamente para los 23 cultivos canónicos. Añadir 20+ cultivos más lo haría enorme y rompería el concepto de "cultivos SIPSA con datos de precios".
- `seed_mercado.py`: está diseñado para poblar `PrecioMercado` + `Comprador` desde `DATOS_MERCADO_HUILA`. Agregar 40+ compradores más lo haría inmanejable.

**Solución**: Crear `apps/mercado/management/commands/seed_huila_completo.py` que:
1. Use `get_or_create` en `CultivoSipsa` para añadir los ~20 cultivos faltantes del Huila (idempotente)
2. Use `update_or_create` en `PrecioMercado` para añadir precios de referencia de los cultivos nuevos
3. Use `update_or_create` en `Comprador` para:
   - Actualizar los 27 compradores existentes con email/whatsapp/sitio_web reales
   - Crear ~20+ compradores nuevos (institucionales, plazas regionales, exportadores)
4. Use `update_or_create` en `PrecioSemanal` para generar 8 semanas de historial de los cultivos nuevos
5. Recalcule predicciones al final

**Idempotencia**: todo por `get_or_create` / `update_or_create` → seguro de correr múltiples veces.

### Estrategia para datos de los nuevos cultivos

- **Precios de referencia**: valores representativos del mercado del Huila (datos históricos SIPSA disponibles públicamente). No se necesita API externa para el seed inicial.
- **Compradores**: datos de entidades reales del Huila (nombre oficial, teléfono institucional público, web oficial). No se inventa ningún dato de contacto sensible; se usan únicamente datos públicos.
- **8 semanas de historial**: se genera con serie sintética representativa (tendencia conocida), igual que los cultivos actuales en `seed_sipsa.py`.

---

## 6. Plan de implementación paso a paso

### Archivos a crear:
```
apps/mercado/management/commands/seed_huila_completo.py   (NUEVO — comando principal)
```

### Archivos a modificar:
```
apps/sipsa/management/commands/seed_sipsa.py              (añadir cultivos nuevos del Huila)
apps/mercado/management/commands/seed_mercado.py          (actualizar contactos de compradores existentes)
apps/mercado/views.py                                     (añadir cultivos nuevos a DATOS_MERCADO_HUILA)
```

### Pasos ordenados por dependencia:

**Paso 1** — Ampliar `CULTIVOS_SEED` en `seed_sipsa.py`
- Añadir ~20 cultivos nuevos del Huila con 8 semanas de precios de referencia y categoría correcta
- Campos: `nombre`, `nombre_dane`, `unidad`, `categoria`, `precios` (lista de 8 valores)
- `get_or_create` → idempotente con los 23 existentes
- Archivos: `apps/sipsa/management/commands/seed_sipsa.py`
- Verificar: `python manage.py seed_sipsa` → "≥ 40 cultivos"

**Paso 2** — Añadir entradas en `DATOS_MERCADO_HUILA` en `views.py`
- Para cada cultivo nuevo: `precio_promedio`, `precio_local`, `unidad`, `tendencia`, `variacion`, `fuente`, `historial` (10 meses), `compradores` (lista de compradores nuevos)
- Archivos: `apps/mercado/views.py`
- Verificar: `python manage.py check` → 0 errores de sistema

**Paso 3** — Crear `seed_huila_completo.py`
- Estructura del comando:
  ```python
  from apps.sipsa.models import CultivoSipsa, PrecioSemanal
  from apps.mercado.models import PrecioMercado, Comprador
  from apps.sipsa.management.commands.seed_sipsa import _recalcular_predicciones, _lunes_hace_n_semanas, _label
  ```
- Sección A: `update_or_create` en `PrecioMercado` para todos los cultivos nuevos
- Sección B: `update_or_create` en `Comprador` para compradores nuevos + actualización de contactos de los 27 existentes vacíos
- Sección C: Recalcular predicciones
- Archivos: `apps/mercado/management/commands/seed_huila_completo.py`
- Verificar: `python manage.py seed_huila_completo` → sin errores; `Comprador.objects.count()` ≥ 50

**Paso 4** — Ampliar `FALLBACK_PRECIOS` en `actualizar_sipsa.py`
- Añadir entradas de los cultivos nuevos para que el cron semanal los cubra en fallback
- Archivos: `apps/sipsa/management/commands/actualizar_sipsa.py`
- Verificar: `python manage.py actualizar_sipsa` → "≥ 40 cultivos actualizados"

**Paso 5** — Ampliar `PRECIOS_ACTUALIZADOS_OCT_2026` en `actualizar_precios.py`
- Añadir entradas de los cultivos nuevos con precio, unidad, tendencia, variación, fuente
- Ampliar `CULTIVOS_DANE` con alias de los nuevos cultivos para búsqueda en Socrata
- Archivos: `apps/mercado/management/commands/actualizar_precios.py`
- Verificar: `python manage.py actualizar_precios` → "≥ 40 cultivos actualizados"

**Paso 6** — Verificación integral
```
python manage.py check                          → 0 errores
python manage.py seed_sipsa                     → idempotente, ≥ 40 cultivos
python manage.py seed_huila_completo            → idempotente, ≥ 50 compradores
python manage.py actualizar_sipsa               → ≥ 40 cultivos actualizados
python manage.py actualizar_precios             → ≥ 40 cultivos actualizados
```

---

## 7. Catálogo objetivo completo (~43 cultivos)

```
Tubérculos (4):
  Papa Pastusa ✓, Yuca ✓, Ñame ✗, Batata ✗

Hortalizas (9):
  Tomate Chonto ✓, Cebolla Cabezona ✓, Zanahoria ✓,
  Pimentón ✗, Pepino Cohombro ✗, Ahuyama ✗, Habichuela ✗

Leguminosas (4):
  Fríjol Cargamanto ✓, Fríjol Bola Roja ✗, Arveja Verde ✗

Cereales / Granos (4):
  Arroz Blanco ✓, Maíz Amarillo ✓, Sorgo ✓, Maíz Blanco ✗

Frutas (18):
  Aguacate Hass ✓, Aguacate Común ✓, Plátano Hartón ✓,
  Maracuyá ✓, Lulo ✓, Cholupa ✓, Limón Tahití ✓,
  Guanábana ✓, Papaya ✓, Mango Tommy ✓, Piña Cayena ✓,
  Granadilla ✗, Badea ✗, Banano Común ✗,
  Mandarina ✗, Naranja Valencia ✗, Tamarindo ✗, Gulupa ✗

Industriales (7):
  Café ✓, Cacao ✓, Caña Panelera ✓,
  Soya ✗, Tabaco ✗, Achiote ✗, Stevia ✗
```
✓ = ya en BD (23)  |  ✗ = falta registrar (~20)

---

## 8. Compradores objetivo (~50+ registros)

### Compradores existentes que necesitan datos de contacto completados (27):
Todos los actuales excepto CADEFIHUILA y Surabastos tienen email/whatsapp/sitio_web vacíos.
Se completarán con datos públicos oficiales en `seed_huila_completo.py`.

### Compradores nuevos a crear (~25 nuevos):

| Nombre | Tipo | Municipio | Datos reales disponibles |
|---|---|---|---|
| Gobernación del Huila — Sec. Agricultura | Institucional | Neiva | web pública |
| ICA Huila | Institucional | Neiva | web pública |
| Banco Agrario Neiva | Financiero | Neiva | web pública |
| FINAGRO | Financiero | Neiva | web pública |
| Plaza Mercado El Emporio Garzón | Plaza de Mercado | Garzón | tel público |
| Plaza Mercado La 21 Neiva | Plaza de Mercado | Neiva | tel público |
| Plaza Mercado Pitalito | Plaza de Mercado | Pitalito | tel público |
| Plaza Mercado La Plata | Plaza de Mercado | La Plata | tel público |
| COAGROFRUVER Huila | Cooperativa | Neiva | datos públicos |
| ASOHOCOL Huila | Asociación | Neiva | datos públicos |
| Cooperativa San Isidro | Cooperativa | Isnos | datos públicos |
| APROCAM | Asociación | Campoalegre | datos públicos |
| Trilladora Cristancho | Agroindustria | Neiva | datos públicos |
| Sucafina Colombia S.A. | Exportador | Pitalito | web pública |
| Indupanela Huila | Asociación | Garzón | datos públicos |
| Postobón S.A. Neiva | Agroindustria | Neiva | web pública |
| Harinera del Valle Huila | Agroindustria | Neiva | web pública |
| Bavaria S.A. (granos Huila) | Agroindustria | Neiva | web pública |
| Colombia Export Coffees S.A.S. | Exportador | Pitalito | datos públicos |
| Galería Las Palmas | Plaza de Mercado | Campoalegre | tel público |
| Plaza de Mercado Rivera | Plaza de Mercado | Rivera | tel público |
| Fedecacao Huila | Federación | Neiva | web pública |
| Fedearroz Huila | Federación | Campoalegre | web pública |
| FNC Comité Huila (Fedecafé) | Federación | Neiva | web pública |
| Agronet MADR Huila | Institucional | Neiva | web pública |

---

## 9. Notas de implementación

1. **`seed_sipsa.py` ya usa `get_or_create`** → añadir cultivos nuevos es idempotente con los 23 existentes.

2. **`views.py` ya tiene `DATOS_MERCADO_HUILA`** y la función `_datos_cultivo` lo usa como fallback. Agregar cultivos nuevos al dict hace que aparezcan en la UI inmediatamente incluso antes de correr el seed.

3. **El modelo `Comprador` no necesita migración** — todos los campos requeridos existen. Solo se añaden datos nuevos.

4. **Los compradores existentes con campos vacíos** se actualizan con `update_or_create` usando `nombre` como clave de búsqueda, igual que el seed actual.

5. **`seed_huila_completo.py` es la pieza central nueva**. Importa y reutiliza funciones de `seed_sipsa.py` (`_recalcular_predicciones`, `_lunes_hace_n_semanas`, `_label`) para no duplicar lógica.

6. **Datos de contacto**: se usan únicamente teléfonos, emails y sitios web de dominio público de entidades formales del Huila. No se fabrican datos privados de personas naturales.
