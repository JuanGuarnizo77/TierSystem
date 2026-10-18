# Reporte: Carga de Cultivos y Compradores del Huila

**Fecha:** 2025-01  
**Ejecutado por:** seed_huila_completo + seed_compradores_huila

---

## Resumen de ejecución

| Comando | Estado | Resultado |
|---|---|---|
| `python manage.py seed_huila_completo` | ✅ EXITOSO | 45 cultivos nuevos, 360 precios semanales, predicciones recalculadas |
| `python manage.py seed_compradores_huila` | ✅ EXITOSO | 12 compradores nuevos creados |
| `python manage.py check` | ✅ EXITOSO | 0 errores de sistema |
| Idempotencia seed_huila_completo | ✅ VERIFICADO | 2ª ejecución: 0 nuevos, 45 ya existían |
| Idempotencia seed_compradores_huila | ✅ VERIFICADO | 2ª ejecución: 0 nuevos, 12 actualizados |

---

## FASE A — Migraciones de modelo

**No fue necesaria ninguna migración.** El plan confirmó que `Comprador` ya tiene todos los campos requeridos (`tipo`, `sitio_web`, `email`, `whatsapp`). No se añadió `descripcion` porque el modelo no lo tiene y el usuario no lo solicitó.

---

## FASE B — Catálogo completo de cultivos registrados

**Total: 45 cultivos nuevos** en `CultivoSipsa` (más los 23 ya existentes = ~68 en total)

### Industria / Café (6 nuevos)
| Nombre | Categoria | Precio Min | Precio Max |
|---|---|---|---|
| Café Castillo | Industria | 3800 | 4500 |
| Café Colombia | Industria | 3800 | 4500 |
| Café Caturra | Industria | 3700 | 4300 |
| Café Típica | Industria | 3900 | 4600 |
| Café Borbón | Industria | 4000 | 4800 |
| Café Tabí | Industria | 4000 | 4800 |

### Permanentes / Frutas (5 nuevos)
| Nombre | Categoria | Precio Min | Precio Max |
|---|---|---|---|
| Aguacate Lorena | Frutas | 2000 | 3500 |
| Plátano Dominico | Frutas | 700 | 1100 |
| Banano | Frutas | 600 | 1000 |
| Caña de Azúcar | Industriales | 300 | 500 |
| Palma de Aceite | Industriales | 1200 | 1800 |

### Frutas Exóticas / Pasifloras (10 nuevos)
| Nombre | Categoria | Precio Min | Precio Max |
|---|---|---|---|
| Granadilla | Frutas | 2500 | 4000 |
| Gulupa | Frutas | 3500 | 5500 |
| Badea | Frutas | 1200 | 2000 |
| Curuba | Frutas | 1500 | 2800 |
| Mora | Frutas | 2200 | 4500 |
| Tomate de Árbol | Frutas | 1500 | 2800 |
| Pitahaya Amarilla | Frutas | 5000 | 8000 |
| Mandarina | Frutas | 900 | 1800 |
| Naranja Valencia | Frutas | 700 | 1400 |
| Mango de Hilacha | Frutas | 800 | 1500 |

### Transitorios / Cereales (11 nuevos)
| Nombre | Categoria | Precio Min | Precio Max |
|---|---|---|---|
| Arroz de Riego | Cereales | 1800 | 2200 |
| Arroz Secano | Cereales | 1600 | 2000 |
| Maíz Blanco | Cereales | 1000 | 1400 |
| Fríjol Radical | Leguminosas | 3800 | 5800 |
| Fríjol Bola Roja | Leguminosas | 3500 | 5500 |
| Tabaco Rubio | Industriales | 4000 | 6000 |
| Tabaco Negro | Industriales | 3500 | 5500 |
| Soya | Industriales | 1500 | 2000 |
| Ajonjolí | Industriales | 3000 | 5000 |
| Algodón | Industriales | 2000 | 3000 |

### Hortalizas (8 nuevas)
| Nombre | Categoria | Precio Min | Precio Max |
|---|---|---|---|
| Tomate Larga Vida | Hortalizas | 1400 | 3000 |
| Cebolla Junca | Hortalizas | 1200 | 2200 |
| Cebolla Cabezona Roja | Hortalizas | 1500 | 2500 |
| Pimentón | Hortalizas | 1800 | 3500 |
| Habichuela | Hortalizas | 2000 | 4000 |
| Pepino | Hortalizas | 800 | 1500 |
| Ají | Hortalizas | 2000 | 4000 |
| Cilantro | Hortalizas | 1500 | 3000 |
| Acelga | Hortalizas | 800 | 1800 |

### Tubérculos (3 nuevos)
| Nombre | Categoria | Precio Min | Precio Max |
|---|---|---|---|
| Papa Criolla | Tubérculos | 1200 | 2200 |
| Ñame | Tubérculos | 700 | 1200 |
| Batata | Tubérculos | 600 | 1000 |

### Acuicultura / Peces (2 nuevos)
| Nombre | Categoria | Precio Min | Precio Max |
|---|---|---|---|
| Tilapia | Industria | 6000 | 9000 |
| Trucha | Industria | 8000 | 12000 |

---

## FASE C — Compradores oficiales registrados

**Total 12 compradores creados** (total en BD: 41)

| # | Nombre | Tipo | Contacto | Sitio Web |
|---|---|---|---|---|
| 1 | SURABASTOS S.A. Propiedad Horizontal | Mayorista | 6088703840 | https://www.surabastos.com |
| 2 | CADEFIHUILA — Cooperativa Departamental de Caficultores del Huila | Cooperativa | (608) 871 5151 | https://www.cadefihuila.com.co |
| 3 | Federación Nacional de Cafeteros — Comité Huila | Cooperativa | (608) 871 0060 | https://huila.federaciondecafeteros.org |
| 4 | COOAGROHUILA — Cooperativa Agropecuaria del Huila | Cooperativa | — | — |
| 5 | ASOHECA — Asociación de Reforestadores y Cultivadores de Caucho del Huila | Exportador | — | — |
| 6 | Almacén Central R.S.A. S.A.S | Mayorista | 6088703840 | — |
| 7 | Agrisur Distribuciones Ltda. | Mayorista | — | — |
| 8 | Distribuciones Agropecuarias Mi Campo S.A.S | Mayorista | — | — |
| 9 | ICBF — Encuentros Agroalimentarios Huila | Institucional | 018000918080 | https://www.icbf.gov.co |
| 10 | Gobernación del Huila — Mercados Campesinos Institucionales | Institucional | (608) 873 1012 | https://www.huila.gov.co |
| 11 | Cámara de Comercio del Huila — Ruedas de Negocio | Institucional | (608) 871 2421 | https://www.cchuila.org |
| 12 | CEAGRODEX DEL HUILA S.A. | Exportador | — | — |

---

## FASE D — Resultados de ejecución

### seed_huila_completo (1ª ejecución)
```
=== seed_huila_completo: iniciando ===
[+] 45 cultivos creados
Cultivos — nuevos: 45, ya existían: 0
Precios semanales nuevos: 360
[predicciones calculadas para 68 cultivos totales]
=== seed_huila_completo: completado ===
```

### seed_compradores_huila (1ª ejecución)
```
=== seed_compradores_huila: iniciando ===
[+] 12 compradores creados
Comprador — creados: 12, actualizados: 0
Total compradores en BD: 41
=== seed_compradores_huila: completado ===
```

### manage.py check
```
System check identified no issues (0 silenced).
```

### Verificación de idempotencia
- `seed_huila_completo` (2ª ejecución): 0 nuevos, 45 ya existían ✅
- `seed_compradores_huila` (2ª ejecución): 0 nuevos, 12 actualizados ✅

---

## Archivos creados

| Archivo | Descripción |
|---|---|
| `apps/mercado/management/commands/seed_huila_completo.py` | Comando principal: registra 45 cultivos + precios semanales + PrecioMercado |
| `apps/mercado/management/commands/seed_compradores_huila.py` | Registra 12 compradores oficiales del Huila |

---

## Errores encontrados

Ninguno. Todos los comandos ejecutaron sin errores.

---

## Notas

- No se realizaron cambios al modelo `Comprador` (todos los campos necesarios ya existían).
- La categoría `cultivos_interes` en `Comprador` es TextField (sin M2M) conforme al schema del plan.
- Los compradores sin contacto disponible públicamente tienen `contacto` vacío según datos públicos disponibles.
- El total de cultivos en BD es aproximadamente 68 (23 preexistentes + 45 nuevos).
