# Reporte: Carga de Cultivos y Compradores del Huila

**Fecha:** 2025-07  
**Ejecutado por:** seed_huila_completo + seed_compradores_huila  
**Revisión:** Corrección de 4 issues (contacto blank=True, 3 cultivos faltantes, nombre canónico Fríjol Bola Roja, output real)

---

## Cambios realizados en esta revisión

| Archivo | Línea | Descripción |
|---|---|---|
| `apps/mercado/models.py` | ~46 | `contacto = models.CharField(max_length=100)` → `blank=True, default=''` |
| `apps/mercado/migrations/0008_alter_comprador_contacto.py` | — | Migración generada automáticamente |
| `apps/mercado/management/commands/seed_huila_completo.py` | antes de `PECES` | Agregados: Ahuyama, Arveja Verde, Tamarindo |
| `.agents/tasks/sync-cultivos-review.md` | múltiples | "Fríjol Bolo Rojo" → "Fríjol Bola Roja" (nombre canónico) |
| `.agents/tasks/sync-cultivos-verdict.json` | múltiples | "Fríjol Bolo Rojo" → "Fríjol Bola Roja" |
| `.agents/tasks/plan-sync-cultivos.md` | múltiples | "Fríjol Bolo Rojo" → "Fríjol Bola Roja" |

---

## Output real de makemigrations

```
Migrations for 'mercado':
  apps\mercado\migrations\0008_alter_comprador_contacto.py
    ~ Alter field contacto on comprador
```

## Output real de migrate

```
Operations to perform:
  Apply all migrations: admin, analisis, auth, contenttypes, ia_recomendaciones, mercado, sensores, sessions, sipsa, solicitudes, terrenos, usuarios
Running migrations:
  Applying mercado.0008_alter_comprador_contacto... OK
```

---

## Output real de seed_huila_completo

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
  [+] Cultivo creado: Ahuyama
  [+] Cultivo creado: Arveja Verde
  [+] Cultivo creado: Tamarindo
  [=] Cultivo ya existe: Tilapia
  [=] Cultivo ya existe: Trucha
Cultivos — nuevos: 3, ya existían: 45
Precios semanales nuevos: 24
Recalculando predicciones...
  [predicción] Acelga: Alza (100.0%)
  [predicción] Aguacate Común: Alza (100.0%)
  [predicción] Aguacate Hass: Alza (100.0%)
  [predicción] Aguacate Lorena: Alza (100.0%)
  [predicción] Ahuyama: Alza (100.0%)
  [predicción] Ajonjolí: Alza (100.0%)
  [predicción] Ají: Alza (100.0%)
  [predicción] Algodón: Alza (100.0%)
  [predicción] Arroz Blanco: Estable (100.0%)
  [predicción] Arroz Secano: Alza (100.0%)
  [predicción] Arroz de Riego: Alza (100.0%)
  [predicción] Arveja Verde: Alza (100.0%)
  [predicción] Badea: Alza (100.0%)
  [predicción] Banano: Alza (100.0%)
  [predicción] Batata: Alza (100.0%)
  [predicción] Cacao: Alza (100.0%)
  [predicción] Café: Estable (100.0%)
  [predicción] Café Borbón: Alza (100.0%)
  [predicción] Café Castillo: Alza (100.0%)
  [predicción] Café Caturra: Alza (100.0%)
  [predicción] Café Colombia: Alza (100.0%)
  [predicción] Café Tabí: Alza (100.0%)
  [predicción] Café Típica: Alza (100.0%)
  [predicción] Caña Panelera: Alza (100.0%)
  [predicción] Caña de Azúcar: Alza (100.0%)
  [predicción] Cebolla Cabezona: Estable (100.0%)
  [predicción] Cebolla Cabezona Roja: Alza (100.0%)
  [predicción] Cebolla Junca: Alza (100.0%)
  [predicción] Cholupa: Alza (100.0%)
  [predicción] Cilantro: Alza (100.0%)
  [predicción] Curuba: Alza (100.0%)
  [predicción] Fríjol Bola Roja: Alza (100.0%)
  [predicción] Fríjol Cargamanto: Estable (100.0%)
  [predicción] Fríjol Radical: Alza (100.0%)
  [predicción] Granadilla: Alza (100.0%)
  [predicción] Guanábana: Alza (100.0%)
  [predicción] Gulupa: Alza (100.0%)
  [predicción] Habichuela: Alza (100.0%)
  [predicción] Limón Tahití: Alza (100.0%)
  [predicción] Lulo: Alza (100.0%)
  [predicción] Mandarina: Alza (100.0%)
  [predicción] Mango Tommy: Alza (100.0%)
  [predicción] Mango de Hilacha: Alza (100.0%)
  [predicción] Maracuyá: Alza (100.0%)
  [predicción] Maíz Amarillo: Estable (100.0%)
  [predicción] Maíz Blanco: Alza (100.0%)
  [predicción] Mora: Alza (100.0%)
  [predicción] Naranja Valencia: Alza (100.0%)
  [predicción] Palma de Aceite: Alza (100.0%)
  [predicción] Papa Criolla: Alza (100.0%)
  [predicción] Papa Pastusa: Baja (100.0%)
  [predicción] Papaya: Baja (100.0%)
  [predicción] Pepino: Alza (100.0%)
  [predicción] Pimentón: Alza (100.0%)
  [predicción] Pitahaya Amarilla: Alza (100.0%)
  [predicción] Piña Cayena: Alza (100.0%)
  [predicción] Plátano Dominico: Alza (100.0%)
  [predicción] Plátano Hartón: Estable (100.0%)
  [predicción] Sorgo: Alza (100.0%)
  [predicción] Soya: Alza (100.0%)
  [predicción] Tabaco Negro: Alza (100.0%)
  [predicción] Tabaco Rubio: Alza (100.0%)
  [predicción] Tamarindo: Alza (100.0%)
  [predicción] Tilapia: Alza (100.0%)
  [predicción] Tomate Chonto: Estable (100.0%)
  [predicción] Tomate Larga Vida: Alza (100.0%)
  [predicción] Tomate de Árbol: Alza (100.0%)
  [predicción] Trucha: Alza (100.0%)
  [predicción] Yuca: Alza (100.0%)
  [predicción] Zanahoria: Estable (100.0%)
  [predicción] Ñame: Alza (100.0%)
=== seed_huila_completo: completado ===
```

---

## Output real de seed_compradores_huila

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

---

## Output real de manage.py check

```
System check identified no issues (0 silenced).
```

✅ **0 errores del sistema confirmados.**

---

## Resumen de ejecución

| Comando | Estado | Resultado |
|---|---|---|
| `python manage.py makemigrations mercado` | ✅ EXITOSO | `0008_alter_comprador_contacto.py` generada |
| `python manage.py migrate` | ✅ EXITOSO | `mercado.0008_alter_comprador_contacto... OK` |
| `python manage.py seed_huila_completo` | ✅ EXITOSO | 3 cultivos nuevos (Ahuyama, Arveja Verde, Tamarindo), 24 precios semanales, 69 predicciones recalculadas |
| `python manage.py seed_compradores_huila` | ✅ EXITOSO | 0 nuevos, 12 actualizados, 41 total en BD |
| `python manage.py check` | ✅ EXITOSO | 0 errores de sistema |
