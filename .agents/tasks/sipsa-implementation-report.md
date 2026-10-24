# SIPSA Implementation Report

## Summary

Three files were modified, 224 new `PrecioSemanal` records were created (28 crops × 8 weeks), 5 new crops were added, and all 14 tests pass.

---

## 1. Precios actualizados por cultivo (week-8 = referencia oficial oct-2026)

| Cultivo | Precio w8 (COP/kg) | Tendencia | Fuente |
|---------|-------------------|-----------|--------|
| Papa Pastusa | 1.900 | Baja | Fedepapa |
| Tomate Chonto | 3.000 | Baja | SIPSA/DANE |
| Cebolla Cabezona | 1.200 | Baja | SIPSA/DANE |
| Fríjol Cargamanto | 8.400 | Alza | SIPSA/DANE |
| Zanahoria | 1.290 | Baja | SIPSA/DANE |
| Plátano Hartón | 980 | Alza | SIPSA/DANE |
| Arroz Blanco | 3.000 | Estable | Fedearroz |
| Maíz Amarillo | 1.400 | Alza | SIPSA/DANE |
| Aguacate Hass | 8.197 | Alza | Asohofrucol |
| Yuca | 1.000 | Alza | SIPSA/DANE |
| Café | 16.440 | **Baja** | FNC |
| Cacao | 14.805 | **Baja** | Fedecacao |
| Aguacate Común | 3.200 | Alza | SIPSA/DANE |
| Caña Panelera | 4.200 | Alza | SIPSA/DANE |
| Maracuyá | 2.000 | Alza | SIPSA/DANE |
| Lulo | 2.800 | Alza | SIPSA/DANE |
| Cholupa | 4.500 | Alza | SIPSA/DANE |
| Sorgo | 1.100 | Estable | SIPSA/DANE |
| Limón Tahití | 1.800 | Alza | SIPSA/DANE |
| Guanábana | 3.800 | Alza | SIPSA/DANE |
| Papaya | 1.500 | Baja | SIPSA/DANE |
| Mango Tommy | 2.200 | Alza | SIPSA/DANE |
| Piña Cayena | 1.600 | Alza | SIPSA/DANE |
| **Fríjol Bola Roja** (nuevo) | 6.500 | Alza | SIPSA/DANE |
| **Granadilla** (nuevo) | 3.500 | Alza | SIPSA/DANE |
| **Pitahaya** (nuevo) | 7.500 | Alza | SIPSA/DANE |
| **Gulupa** (nuevo) | 5.000 | Alza | SIPSA/DANE |
| **Mora** (nuevo) | 4.500 | Alza | SIPSA/DANE |

### Correcciones clave vs versión anterior
- Café: 16440 (sin cambio en precio) pero tendencia corregida de **Alza → Baja** (serie histórica invertida: ahora desciende de 17200 a 16440)
- Cacao: 14826 → **14805**, tendencia corregida de Alza → Baja
- Papa Pastusa: 2260 → **1900**
- Cebolla Cabezona: 3120 → **1200** (tanto en FALLBACK como en mercado)
- Fríjol Cargamanto: 11750/12800 → **8400**
- Plátano Hartón: 1820/1750 → **980**
- Arroz Blanco: 2120/2200 → **3000**
- Maíz Amarillo: 1510/1680 → **1400**
- Aguacate Hass: 7300/7200 → **8197**
- Yuca: 980/995 → **1000**
- Maracuyá: 2800 → **2000**
- Lulo: 3500 → **2800**

---

## 2. Cambios en el formato de fechas

### Antes
```
Sem 42-2026
```

### Después
```
12 oct – 18 oct 2026
```

### Archivos modificados
- `apps/sipsa/management/commands/seed_sipsa.py` — función `_label()` reemplazada por versión con rango de fechas + array `MESES_ES`
- `apps/sipsa/management/commands/actualizar_sipsa.py` — mismo cambio en `_label()` + `MESES_ES`
- `apps/mercado/management/commands/actualizar_precios.py` — constante `SEMANA_LABEL` eliminada; reemplazada por función `_semana_label_actual()` que calcula el rango dinámicamente en cada ejecución

### Verificación
Spot-check en BD:
```
Café:         label=12 oct – 18 oct 2026 ✓
Papa Pastusa: label=12 oct – 18 oct 2026 ✓
```

---

## 3. Verificación del motor de predicción (`prediccion.py`)

El motor no requirió cambios. Verificaciones:

| Aspecto | Estado |
|---------|--------|
| División por cero con < 2 semanas | ✅ Protegido — retorna Estable con confianza 0 |
| Regresión lineal (mínimos cuadrados) | ✅ Correcta — denominador protegido contra cero |
| Umbrales Alza/Baja/Estable | ✅ ±0.5%/semana — con 8 semanas de datos reales los cultivos clasifican correctamente |
| Probabilidad 0–100 | ✅ `min(100.0, (n / 8) * 100)` |
| Predicciones correctas post-seed | Café: Baja (-0.43%) ✓ | Cacao: Baja (-1.35%) ✓ |

---

## 4. Resultado `python manage.py check`

```
System check identified no issues (0 silenced).
```

---

## 5. Suite de tests

```
Ran 14 tests in 5.644s
OK
```

Todos los tests pasan sin modificar el archivo de tests.

---

## 6. Otros cambios de `seed_sipsa.py`

- `PrecioSemanal.objects.get_or_create` → **`update_or_create`** para que las re-ejecuciones del seed actualicen precios existentes en lugar de ignorarlos
- 671 registros stale eliminados antes del re-seed; 224 nuevos registros creados (28 cultivos × 8 semanas)
- `CULTIVOS_SEED` amplificado de 23 a 28 entradas con los 5 cultivos faltantes del brief

---

*Generado: 2026-10-12*
