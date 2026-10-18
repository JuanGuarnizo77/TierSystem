# Implementation Plan — Sistema de Precios Reales Módulo Mercado

## Hallazgos de exploración (base del plan)

- `apps/mercado/models.py` **ya declara** `PrecioMercado` y `Comprador`. El modelo `PrecioMercado` tiene `fecha_actualizacion = DateTimeField(auto_now=True)` pero le faltan `semana_sipsa`, `fuente_url` y `ultima_actualizacion`. El modelo `Comprador` existe pero no tiene `email`, `whatsapp` ni `sitio_web`.
- Migraciones existentes: `0001_initial`, `0002_comprador_preciomercado`, `0003_alter_comprador_contacto_and_more`. La nueva migración será `0004_…`.
- `apps/mercado/views.py` ya tiene la vista `precios_sipsa` con lógica de indicador de conexión usando `fecha_actualizacion__gte` (DateTimeField 24h) — pero la tarea pide usar el nuevo campo `ultima_actualizacion` y extenderlo a 72h.
- `apps/mercado/urls.py` **ya tiene** `path('api/cultivo/<str:cultivo_nombre>/', ...)` — NO duplicar. Solo añadir `path('actualizar/', views.actualizar_precios_view, name='actualizar_precios')`.
- `seed_mercado.py` usa `get_or_create` — para actualizar contactos de compradores ya existentes se necesita `filter().update()` o `update_or_create`.
- `requirements.txt` tiene solo `Django>=4.2,<5.0` sin las librerías de scraping. Estas ya están instaladas en el venv según el brief, pero el archivo no las refleja.
- El directorio `apps/mercado/management/commands/` ya existe con `__init__.py`.
- Django 5.2 en venv; settings en `tiersystem/settings.py`; DJANGO_SETTINGS_MODULE a exportar antes de comandos.

---

## Plan

- [ ] 1. Añadir campos nuevos a `PrecioMercado` y `Comprador` en `apps/mercado/models.py`.
      A la clase `PrecioMercado` agregar al final (justo antes del `__str__`):
      ```python
      semana_sipsa = models.CharField(max_length=100, blank=True, default='')
      fuente_url   = models.CharField(max_length=500, blank=True, default='')
      ultima_actualizacion = models.DateTimeField(auto_now=True)
      ```
      A la clase `Comprador` agregar al final (antes del `__str__`):
      ```python
      email      = models.EmailField(blank=True, default='')
      whatsapp   = models.CharField(max_length=20, blank=True, default='')
      sitio_web  = models.CharField(max_length=200, blank=True, default='')
      ```
      No eliminar ningún campo existente. No cambiar ningún campo existente.
      Archivos: `apps/mercado/models.py`
      Verificar: `$env:DJANGO_SETTINGS_MODULE='tiersystem.settings'; .\venv\Scripts\python.exe -c "import django; django.setup(); from apps.mercado.models import PrecioMercado, Comprador; print([f.name for f in PrecioMercado._meta.get_fields()])"` — la salida debe incluir `semana_sipsa`, `fuente_url`, `ultima_actualizacion`. Y para `Comprador`: debe incluir `email`, `whatsapp`, `sitio_web`.

- [ ] 2. Crear y aplicar la migración `0004` para los campos nuevos.
      Ejecutar en orden (desde el directorio raíz `c:\Users\punto\Desktop\tyersistem clon`):
      ```powershell
      $env:DJANGO_SETTINGS_MODULE='tiersystem.settings'
      .\venv\Scripts\python.exe manage.py makemigrations mercado
      .\venv\Scripts\python.exe manage.py migrate
      ```
      El archivo generado estará en `apps/mercado/migrations/0004_*.py` y debe añadir `AddField` para los 6 campos nuevos (3 en `PrecioMercado`, 3 en `Comprador`). Todos usan `default=''` o `auto_now=True` por lo que Django no pedirá valores en la migración.
      Archivos: `apps/mercado/migrations/0004_*.py` (generado automáticamente)
      Verificar: `.\venv\Scripts\python.exe manage.py showmigrations mercado` muestra `[X] 0004_…` con la X marcada. `.\venv\Scripts\python.exe manage.py check` devuelve `System check identified no issues (0 silenced).`

- [ ] 3. Crear `apps/mercado/management/commands/actualizar_precios.py` con el comando de actualización.
      Crear el archivo completo con las secciones exactas del brief:
      - Clase `Command(BaseCommand)` con `help = 'Actualiza precios de mercado desde FNC, Agronet y SIPSA/DANE'`.
      - Método `handle()` que llama a `actualizar_cafe()`, `actualizar_cacao()`, y a la lógica de APIs Socrata + fallback para los demás cultivos.
      - Método `actualizar_cafe(self)` con el scraping de `preciocafe.com` (regex `r'[\$]?\s*([\d]{1}[.,\d]{6,9})'`) y la validación `800000 < precio_carga < 8000000`.
      - Método `actualizar_cacao(self)` con el scraping de Agronet y los tres patrones regex del brief.
      - Constante `APIS_SOCRATA` con las tres URLs del brief. Lógica que itera las tres, detecta JSON válido con lista no vacía, busca campos de cultivo (`producto`, `alimento`, `cultivo`) y precio (`precio`, `valor`, `precio_promedio`), filtra por `'Neiva'` o `'Huila'`.
      - Constante `PRECIOS_ACTUALIZADOS_OCT_2026` con los 9 cultivos y sus valores exactos del brief.
      - Método `_guardar_precio(self, cultivo_nombre, precio_promedio, precio_local, unidad, fuente, fuente_url='', semana='')` exactamente como está en el brief, incluyendo el cálculo de tendencia y variación comparando con el registro anterior, y el `update_or_create` con los campos `semana_sipsa`, `fuente_url`.
      - El `handle()` debe: (1) intentar `actualizar_cafe()` y `actualizar_cacao()`; (2) intentar cada API Socrata con timeout=10 para el resto de cultivos; (3) si todas las APIs fallan, aplicar `PRECIOS_ACTUALIZADOS_OCT_2026` con `_guardar_precio()`; (4) imprimir resumen final con `self.style.SUCCESS`.
      Todos los bloques de red envueltos en `try/except Exception as e` con `self.stdout.write(self.style.WARNING(...))`.
      Archivos: `apps/mercado/management/commands/actualizar_precios.py`
      Verificar: `$env:DJANGO_SETTINGS_MODULE='tiersystem.settings'; .\venv\Scripts\python.exe manage.py actualizar_precios 2>&1` — corre sin traceback, imprime líneas `✓ Cultivo: $X/unidad (fuente)` y un resumen final. Los warnings de red son aceptables.

- [ ] 4. Actualizar `apps/mercado/management/commands/seed_mercado.py` para añadir datos de contacto a los compradores.
      Después del bloque de creación de compradores (bucle `for nombre, datos_c in compradores_map.items():`), agregar un bloque que actualice los campos de contacto para compradores ya existentes. Usar `update_or_create` o `filter(nombre__icontains=...).update(...)`:
      - Para CADEFIHUILA (buscar `nombre__icontains='CADEFIHUILA'`): `email='info@cadefihuila.com'`, `whatsapp='3105554321'`, `sitio_web='https://cadefihuila.com'`
      - Para Surabastos (buscar `nombre__icontains='Surabastos'`): `email='comercial@surabastos.com.co'`, `whatsapp='3187891234'`, `sitio_web='https://surabastos.com.co'`
      - Para los demás compradores no cubiertos: los campos quedan en `blank=True, default=''` establecido por la migración, no es necesario actualizarlos.
      El bloque de actualización de contactos va **después** del bucle principal de `get_or_create`, para que funcione tanto en una corrida fresca como en re-ejecuciones sobre datos existentes.
      Archivos: `apps/mercado/management/commands/seed_mercado.py`
      Verificar: `$env:DJANGO_SETTINGS_MODULE='tiersystem.settings'; .\venv\Scripts\python.exe manage.py seed_mercado 2>&1` — corre sin errores; luego `.\venv\Scripts\python.exe -c "import django; django.setup(); from apps.mercado.models import Comprador; c=Comprador.objects.filter(nombre__icontains='CADEFIHUILA').first(); print(c.email, c.whatsapp)"` imprime `info@cadefihuila.com 3105554321`.

- [ ] 5. Reescribir `templates/agricultor/precios_sipsa.html` con la nueva interfaz completa.
      Reemplazar el contenido actual (tabla simple de 4 columnas sin detalles ni botón de actualización) con la interfaz nueva que incluye:
      **Header del módulo:**
      - Título `Mercado Mayorista SIPSA`, subtítulo con `{{ fecha_hoy }}` / `{{ ultima_actualizacion_global }}`.
      - Botón `Actualizar Precios` con JS que hace `fetch('/mercado/actualizar/', {method:'POST', headers:{'X-CSRFToken': csrftoken}})` y recarga la página en `.then()`.
      - Badge de estado: verde si `estado_conexion == 'online'`, amarillo si `estado_conexion == 'reciente'`, rojo si `estado_conexion == 'desactualizado'`.

      **Tabla de cultivos:**
      - Columnas: Cultivo, Precio promedio ($/unidad), Precio local, Unidad, Tendencia (badge), Variación %, Fuente, Actualizado.
      - Iterar `{% for item in precios_tabla %}` donde cada `item` tiene `cultivo`, `precio_promedio`, `precio_local`, `unidad`, `tendencia`, `variacion_porcentaje`, `fuente`, `ultima_actualizacion`.
      - Badge tendencia: verde con `↑ Alza`, rojo con `↓ Baja`, gris con `— Estable`.
      - Indicador frescura por fila: calcular en el template con `{% if item.dias_desde_actualizacion <= 1 %}` verde `Hoy`, `{% elif <= 7 %}` amarillo `Esta semana`, `{% else %}` rojo `Desactualizado`. Nota: `dias_desde_actualizacion` se calcula en la vista y se pasa en cada item del contexto.
      - Fila clickeable: `onclick="toggleDetalle('{{ item.cultivo }}')"` que muestra/oculta un `<tr id="detalle-{{ item.cultivo }}">`.

      **Panel detalle expandible (dentro de la tabla, segunda fila por cultivo):**
      - Gráfica de historial 6 meses con barras CSS (divs `style="height: {{ h.pct }}%"`), usando `item.historial`.
      - Lista de compradores con nombre, tipo, municipio, teléfono clickeable (`tel:`), botón WhatsApp verde si `c.whatsapp` existe (`https://wa.me/57{{ c.whatsapp }}`), email (`mailto:`) si existe, sitio web si existe, precio_referencia.
      - Los datos de compradores por cultivo vienen en `item.compradores` (lista de dicts con `nombre`, `tipo`, `municipio`, `contacto`, `whatsapp`, `email`, `sitio_web`, `precio_referencia`).

      **Footer de fuentes:**
      - Texto fijo: `Fuentes: FNC, Fedecacao/Agronet, SIPSA/DANE — Actualizado: {{ fecha_hoy }}`
      - NO incluir indicador ONLINE/OFFLINE del antiguo diseño.

      Tailwind, colores `#0a4d3c` para primary, dark mode compatible. Mismo estilo `bento-card` que el sistema actual.
      Archivos: `templates/agricultor/precios_sipsa.html`
      Verificar: `$env:DJANGO_SETTINGS_MODULE='tiersystem.settings'; .\venv\Scripts\python.exe -c "import django; django.setup(); from django.template.loader import get_template; get_template('agricultor/precios_sipsa.html'); print('Template OK')"` imprime `Template OK` sin errores de sintaxis Jinja/Django.

- [ ] 6. Actualizar `apps/mercado/views.py`: añadir `actualizar_precios_view` y mejorar `precios_sipsa`.
      **Añadir la vista `actualizar_precios_view`** exactamente como aparece en el brief:
      ```python
      @login_required(login_url='login')
      def actualizar_precios_view(request):
          if request.method == 'POST':
              if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
                  return JsonResponse({'error': 'No autorizado'}, status=403)
              try:
                  from django.core.management import call_command
                  import io
                  out = io.StringIO()
                  call_command('actualizar_precios', stdout=out)
                  return JsonResponse({'mensaje': 'Precios actualizados correctamente', 'detalle': out.getvalue()})
              except Exception as e:
                  return JsonResponse({'error': str(e)}, status=500)
          return JsonResponse({'error': 'Método no permitido'}, status=405)
      ```
      **Modificar la vista `precios_sipsa`** en el bloque del indicador de conexión:
      - Cambiar el filtro de `fecha_actualizacion__gte` a `ultima_actualizacion__gte` (nuevo campo).
      - Cambiar el umbral de 24h a 72h: `timedelta(hours=72)`.
      - Agregar lógica de tres estados: `online` (datos ≤ 24h), `reciente` (datos 24h-72h), `desactualizado` (>72h o sin datos).
      - Construir `precios_tabla`: lista de dicts con todos los campos necesarios para la tabla nueva, incluyendo `compradores` (llamando a `_get_compradores_for_cultivo()`) y `historial` (del dict estático `DATOS_MERCADO_HUILA`), y `dias_desde_actualizacion` (calculado como `(timezone.now() - pm.ultima_actualizacion).days`).
      - Pasar `ultima_actualizacion_global` al contexto: la `ultima_actualizacion` del registro más reciente (o `None`).
      Archivos: `apps/mercado/views.py`
      Verificar: `$env:DJANGO_SETTINGS_MODULE='tiersystem.settings'; .\venv\Scripts\python.exe manage.py check` devuelve `System check identified no issues (0 silenced).`

- [ ] 7. Registrar `actualizar/` en `apps/mercado/urls.py`.
      Añadir exactamente esta línea al `urlpatterns` (la ruta `api/cultivo/` ya existe, no tocarla):
      ```python
      path('actualizar/', views.actualizar_precios_view, name='actualizar_precios'),
      ```
      Archivos: `apps/mercado/urls.py`
      Verificar: `$env:DJANGO_SETTINGS_MODULE='tiersystem.settings'; .\venv\Scripts\python.exe -c "import django; django.setup(); from apps.mercado.urls import urlpatterns; print([u.name for u in urlpatterns])"` — la salida incluye `'actualizar_precios'` y sigue teniendo `'api_datos_cultivo'` (sin duplicados).

---

## Verificación final global

Ejecutar en orden después de completar los 7 pasos:
```powershell
$env:DJANGO_SETTINGS_MODULE='tiersystem.settings'
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe -c "import django; django.setup(); from django.template.loader import get_template; get_template('agricultor/precios_sipsa.html'); print('Template OK')"
.\venv\Scripts\python.exe manage.py actualizar_precios 2>&1
.\venv\Scripts\python.exe manage.py seed_mercado 2>&1
```
Resultado esperado: `check` sin errores, `Template OK`, `actualizar_precios` sin traceback, `seed_mercado` con contactos de CADEFIHUILA y Surabastos.

---

## Orden de dependencias

```
1 (añadir campos al modelo) → 2 (makemigrations + migrate)
2 → 3 (actualizar_precios usa semana_sipsa, fuente_url, ultima_actualizacion)
2 → 4 (seed_mercado actualiza email/whatsapp/sitio_web que existen tras la migración)
2 → 6 (views.py usa ultima_actualizacion en el filtro ORM)
5 (template) depende de 6 (los nombres de variables del contexto)
7 (urls.py) depende de 6 (la vista debe existir antes de registrarla)
3, 4, 5, 7 son independientes entre sí una vez que 1+2 están listos
```

Orden recomendado: **1 → 2 → 3 → 4 → 6 → 5 → 7 → Verificación final**

---

## Decisiones de diseño

- **`ultima_actualizacion` como campo separado de `fecha_actualizacion`**: `fecha_actualizacion` ya existe (DateTimeField auto_now) y las migraciones previas dependen de él. Añadir `ultima_actualizacion` como campo adicional es más seguro que renombrar, y permite que el template y las views lo referencien con el nombre exacto indicado en el brief.
- **Tres estados de conexión en vez de dos**: el brief especifica verde/amarillo/rojo para hoy/esta-semana/>3días. Se mapea a `online`/`reciente`/`desactualizado` en el contexto y se distingue en el template con tres bloques `{% if %}`.
- **`precios_tabla` como lista de dicts enriquecidos**: la vista construye `precios_tabla` completa (con compradores e historial) en vez de que el template haga múltiples llamadas a la BD, para mantener la lógica en Python y el template simple.
- **`update_or_create` para contactos en seed_mercado**: el bloque de actualización de contactos usa `filter().update()` para que sea idempotente y funcione aunque el comprador ya exista de corridas anteriores de `seed_mercado`.
- **No tocar otros templates ni otras apps**: todo el trabajo está en `apps/mercado/` y `templates/agricultor/precios_sipsa.html`.
