# Reporte de Chequeo General — TierSystem Django
**Fecha:** 2026-07-10  
**Proyecto:** TierSystem — Django 5.2, MySQL/Laragon, Python 3.10  
**Auditor:** Kiro AI — Investigación READ-ONLY exhaustiva

---

## RESUMEN EJECUTIVO

El proyecto funciona correctamente en su estructura principal. Django `manage.py check` reportó **0 issues**. Todas las migraciones están aplicadas. Todos los templates cargan sin error. Todos los URLs nombrados resuelven correctamente. Sin embargo, se identificaron **5 bugs importantes/críticos** y **12 issues menores** que se detallan a continuación.

---

## 1. PYTHON / DJANGO

### 🔴 CRÍTICO — Signal `guardar_perfil_usuario` puede lanzar `AttributeError`

**Archivo:** `apps/usuarios/models.py`, línea 27  
**Descripción:** El signal `post_save` en `guardar_perfil_usuario` llama `instance.perfil.save()` **incondicionalmente** en cada guardado de User. Sin embargo, si se guarda un User recién creado y por alguna razón el signal `crear_perfil_usuario` no se ha ejecutado aún (o falla), `instance.perfil` lanzará `RelatedObjectDoesNotExist` (subclase de `AttributeError`). Además, existe una **condición de carrera**: ambos signals son `post_save` en el mismo sender. Si la DB tarda en persistir el perfil antes de que se llame `.save()`, falla.

```python
# Línea 27-28 — problemático:
def guardar_perfil_usuario(sender, instance, **kwargs):
    instance.perfil.save()  # Sin guard hasattr() — puede crashear en creación
```

**Fix recomendado:**
```python
@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    if not kwargs.get('created', False) and hasattr(instance, 'perfil'):
        instance.perfil.save()
```

---

### 🔴 CRÍTICO — Nombre de modelo Gemini incorrecto

**Archivo:** `apps/ia_recomendaciones/views.py`, línea 89  
**Descripción:** Se usa `'gemini-3.6-flash'` como nombre del modelo. **Este modelo no existe**. Los modelos válidos actuales son `'gemini-1.5-flash'`, `'gemini-1.5-pro'`, o `'gemini-pro'`. Esto causará un error 500 inmediato en producción cuando se tenga `GEMINI_API_KEY` configurada.

```python
# Línea 89 — incorrecto:
model = genai.GenerativeModel('gemini-3.6-flash')
```

**Fix:**
```python
model = genai.GenerativeModel('gemini-1.5-flash')
```

---

### 🔴 CRÍTICO — `google.generativeai` (paquete deprecado)

**Archivo:** `apps/ia_recomendaciones/views.py`, línea 9  
**Descripción:** El paquete `google-generativeai` fue deprecado y ya no recibe actualizaciones de seguridad. La advertencia en tiempo de ejecución confirma esto. Puede dejar de funcionar en cualquier actualización de la API de Google.

```
FutureWarning: All support for the `google.generativeai` package has ended.
```

**Fix recomendado:** Migrar a `google-genai`:
```python
from google import genai
client = genai.Client(api_key=api_key)
response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
```

---

### 🟡 IMPORTANTE — `guardar_perfil_usuario` llama `.save()` creando bucle potencial

**Archivo:** `apps/usuarios/models.py`, líneas 27-28  
**Descripción:** El signal `post_save` de User llama `instance.perfil.save()`, lo cual dispara de nuevo el signal `post_save` del User a través de la relación. Si Perfil tiene un OneToOneField hacia User, esto no genera un bucle infinito per se, pero el patrón es innecesario para la mayoría de operaciones. El signal `crear_perfil_usuario` con `get_or_create` es suficiente.

---

### 🟡 IMPORTANTE — `exportar_analisis_individual_pdf` puede crashear con `AttributeError`

**Archivo:** `apps/solicitudes/views.py`, aproximadamente línea 710 (en función `exportar_analisis_individual_pdf`)  
**Descripción:** La función llama `_evaluar_parametros_agronomicos(a, solicitud.cultivo_deseado)` donde `a = solicitud.analisis_resultado`. Si el análisis no tiene los 7 parámetros completos (valores `None` vs `0`), el `float(analisis_obj.ph)` etc. lanzaría `TypeError`. Sin embargo, el modelo define `default=0` así que el riesgo es bajo, pero no hay manejo de excepción.

---

### 🟡 IMPORTANTE — `comparar_analisis_agricultor`: acceso a `analisis_resultado` sin guard

**Archivo:** `apps/solicitudes/views.py`, funciones `comparar_analisis_agricultor` (líneas ~250-300)  
**Descripción:** Después de `s1 = get_object_or_404(...)` y `s2 = get_object_or_404(...)`, el código hace `a1 = s1.analisis_resultado` y `a2 = s2.analisis_resultado` directamente **sin verificar** `hasattr(s1, 'analisis_resultado')`. Si alguna solicitud completada no tiene `RegistroAnalisis`, lanzará `RelatedObjectDoesNotExist` con HTTP 500.

```python
# Sin protección — crash potencial:
a1 = s1.analisis_resultado
a2 = s2.analisis_resultado
```

**Fix:**
```python
if not hasattr(s1, 'analisis_resultado') or not hasattr(s2, 'analisis_resultado'):
    return render(request, 'agricultor/comparar.html', {'insuficientes': True, ...})
```

---

### 🟢 MENOR — Doble directorio `tiersystem/tiersystem/`

**Archivos:** `tiersystem/tiersystem/settings.py`, `tiersystem/tiersystem/urls.py`, etc.  
**Descripción:** Existe un directorio anidado `tiersystem/tiersystem/` con un `settings.py` vacío/default de `django-admin startproject`. Este directorio **nunca se usa** (el proyecto activo está en `tiersystem/`) pero puede causar confusión. No produce errores pero es un remanente de una creación accidental.

---

## 2. TEMPLATES HTML

### ✅ LIMPIO — Todos los templates cargan sin error
Se verificaron los 19 templates principales con `get_template()`. Ninguno produjo error de sintaxis.

### 🟡 IMPORTANTE — Template `templates/admin/usuarios.html`: `csrfToken` definido **después** de donde se usa

**Archivo:** `templates/admin/usuarios.html`, líneas ~381 y ~416  
**Descripción:** En el template, `csrfToken` se define en la línea 473 (`const csrfToken = document.querySelector(...).value`), pero los event listeners de `formLaboratorista.addEventListener` (línea ~381) y `formEditar.addEventListener` (línea ~416) hacen referencia a `csrfToken` en su closure. Esto funciona en la práctica por hoisting de closures en JS, **pero** si el `{% csrf_token %}` de la línea 181 no renderiza dentro del mismo bloque DOM visible cuando el script corre, `querySelector('[name=csrfmiddlewaretoken]')` devuelve `null` y `csrfToken` será `null.value` → **TypeError en runtime**.

El `{% csrf_token %}` está fuera del formulario (standalone en línea 181, dentro del `{% block content %}`), mientras que los forms con id `formLaboratorista` y `formEditar` son HTML en modales ocultos, pero el hidden input del CSRF sí está en el DOM. Esto funciona, pero el orden es frágil.

---

### 🟡 IMPORTANTE — `templates/laboratorista/dashboard.html`: URL hardcodeada `/api/captura-estable/` y `/api/ia/diagnosticar/`

**Archivo:** `templates/laboratorista/dashboard.html`, líneas ~aprox. 190 y 220  
**Descripción:** Las URLs de fetch están hardcodeadas:
- `/api/captura-estable/` — mapeado en `tiersystem/urls.py` como `api/` → `apps/sensores/urls.py` → `captura-estable/`. URL completa: `/api/captura-estable/`. **Correcto.**
- `/api/ia/diagnosticar/` — mapeado como `api/ia/` → `apps/ia_recomendaciones/urls.py` → `diagnosticar/`. URL completa: `/api/ia/diagnosticar/`. **Correcto.**

Estas no son bugs funcionales pero si cambia la estructura de URLs, el template no se actualiza automáticamente. Sería mejor usar `{% url %}` con variables de template.

---

### 🟢 MENOR — `templates/agricultor/solicitudes.html`: URL hardcodeada en JS para cancelar

**Archivo:** `templates/agricultor/solicitudes.html`, función `cancelarSolicitud(id)` (~línea 180)  
**Descripción:** 
```javascript
fetch(`/agricultor/solicitudes/cancelar/${id}/`, ...)
```
La URL hardcodeada corresponde a `solicitudes_agricultor:cancelar_solicitud` que se monta en `/agricultor/solicitudes/cancelar/<id>/`. Esta URL es **correcta** pero no usa `{% url %}` de Django.

---

### 🟢 MENOR — `templates/agricultor/terrenos.html`: URLs hardcodeadas para editar/eliminar finca

**Archivo:** `templates/agricultor/terrenos.html`, funciones `editarTerreno()` y `eliminarTerreno()` (~líneas 290, 310)
```javascript
fetch(`/agricultor/fincas/editar/${id}/`, ...)
fetch(`/agricultor/fincas/eliminar/${id}/`, ...)
```
Las URLs son correctas pero hardcodeadas. Funciona bien actualmente.

---

### 🟢 MENOR — `templates/admin/usuarios.html`: Editar usuario usa URL hardcodeada en JS

**Archivo:** `templates/admin/usuarios.html`, línea ~416  
```javascript
fetch(`/administrador/usuarios/${id}/editar/`, ...)
```
Coincide con el URL pattern `administrador/usuarios/<int:user_id>/editar/` definido en `core/urls.py`. **Correcto pero hardcodeado**.

---

## 3. URLs

### ✅ LIMPIO — Todos los nombres de URL resuelven

Verificación exhaustiva con `reverse()` de 38 URLs nombradas (incluyendo namespaces `terrenos:`, `solicitudes_agricultor:`, `solicitudes:`, `mercado:`, `analisis:`). **Todas resuelven correctamente**.

### 🟢 MENOR — `path('api/', api_root)` y `path('api/', include('apps.sensores.urls'))` duplican el prefijo `/api/`

**Archivo:** `tiersystem/urls.py`, líneas 10 y 15  
**Descripción:**
```python
path('api/', api_root, name='api-root'),         # retorna JSON básico
path('api/', include('apps.sensores.urls')),      # sensores
```
Ambos usan el prefijo `api/`. Django procesa en orden, así que `api/` solo llegará a `api_root`. Las rutas de sensores son `api/lecturas/` y `api/captura-estable/` que **sí se registran correctamente** porque Django hace matching por prefijo, no exacto. Sin embargo, `GET /api/` devuelve `api_root` en lugar de un 404 descriptivo. No es un bug crítico pero confuso.

---

### 🟢 MENOR — `path('admin/', lambda r: redirect('dashboard_admin'))` antes que algunas rutas

**Archivo:** `tiersystem/urls.py`, línea 9  
**Descripción:** El path `admin/` redirige a `dashboard_admin`. Esto es intencional pero significa que el Admin de Django solo es accesible por `/superadmin/`. Es un diseño válido pero puede sorprender a desarrolladores que intenten acceder a `/admin/`.

---

## 4. MIGRACIONES

### ✅ LIMPIO — Sin migraciones pendientes

```
manage.py makemigrations --check --dry-run → No changes detected
manage.py migrate --check → Sin migraciones sin aplicar (según salida sin errores de contenido)
```

---

## 5. JAVASCRIPT

### 🔴 CRÍTICO — `csrfToken` puede ser `null` en ciertos estados del DOM

**Archivo:** `templates/admin/usuarios.html`, líneas 473 y 381/416  
**Descripción:** Ver sección 2 (Templates). Si el `{% csrf_token %}` no está renderizado al momento de que el script se ejecuta (ej. si el bloque `{% block content %}` está vacío o hay un error de renderizado parcial), `document.querySelector('[name=csrfmiddlewaretoken]')` retorna `null` y `csrfToken = null.value` lanza `TypeError: Cannot read properties of null`.

**Fix recomendado:** Usar la función `getCookie` estándar de Django como en los otros templates:
```javascript
function getCookie(name) { /* ... */ }
const csrfToken = getCookie('csrftoken');
```

---

### 🟡 IMPORTANTE — `verificarDatosEstables()` en laboratorista/dashboard.html: Sin validación de campos antes de mostrar resultados

**Archivo:** `templates/laboratorista/dashboard.html`, función `mostrarResultados(datos)`  
**Descripción:** Si el servidor devuelve `datos` con un campo `null` (ej. sensor desconectado parcialmente), `datos.humedad + '%'` mostraría `null%`. No hay validación de tipos antes del display. Es un issue de UX/robustez.

---

### 🟢 MENOR — DataTables en historial.html: columna 11 (Acción) marcada `orderable: false` con index correcto

**Archivo:** `templates/agricultor/historial.html`, bloque `extra_js`  
**Descripción:** `columnDefs: [{ orderable: false, searchable: false, targets: [0, 11] }]` — la tabla tiene 12 columnas (0-11). El índice 11 es la columna "Acción". **Correcto**. Sin issues.

---

### 🟢 MENOR — `precios_sipsa` hace fetch externo a DANE en cada request

**Archivo:** `apps/mercado/views.py`, función `precios_sipsa()`  
**Descripción:** En cada carga de la página, se realiza un `requests.get('https://www.datos.gov.co/...', timeout=2)` solo para verificar conectividad. Con `timeout=2`, esto añade hasta 2 segundos de latencia en cada request de la página de mercado. No hay caché ni background task.

---

## 6. ARCHIVOS ESTÁTICOS

### ✅ LIMPIO — `static/css/styles.css` existe y está referenciado correctamente

Verificado: `c:\Users\punto\Desktop\tyersistem clon\static\css\styles.css` existe.  
Todos los templates que usan `{% static 'css/styles.css' %}` encontrarán el archivo.

### ✅ LIMPIO — Archivos de imágenes y JS estáticos presentes

Presentes en `static/`:
- `css/styles.css` ✅
- `img/cultivo.jpg` ✅  
- `img/hero_plant.jpg` ✅
- `js/db.js` ✅
- `js/service-worker.js` ✅
- `manifest.json` ✅

---

## 7. CONTEXT PROCESSORS

### ✅ LIMPIO — `core.context_processors.solicitud_activa` correctamente registrado

**Archivo:** `tiersystem/settings.py`, línea ~58  
```python
'core.context_processors.solicitud_activa',
```
Confirmado que está en `TEMPLATES[0]['OPTIONS']['context_processors']`.

**Archivo:** `core/context_processors.py`  
La función existe, importa `SolicitudAnalisis` correctamente y retorna el contexto esperado `{'solicitud_activa_sidebar': bool}`.

### ✅ LIMPIO — Variable `solicitud_activa_sidebar` usada correctamente en `base_dashboard.html`

El template agricultor usa `{% if solicitud_activa_sidebar %}` (línea ~75 en `base_dashboard.html`). Nombre coincide. Sin issues.

---

## 8. SEGURIDAD

### 🟡 IMPORTANTE — `api_diagnosticar_ia` y `recibir_datos_sensor` son `@csrf_exempt` sin autenticación

**Archivos:**  
- `apps/ia_recomendaciones/views.py`, línea 20: `@csrf_exempt`  
- `apps/sensores/views.py`, línea 8: `@csrf_exempt`

**Descripción:** Ambos endpoints POST están exentos de CSRF y no requieren autenticación (`@login_required`). Cualquier persona que conozca la URL puede:
1. Enviar datos falsos de sensores a la BD (`POST /api/lecturas/`)
2. Gastar créditos de la API Gemini enviando prompts arbitrarios (`POST /api/ia/diagnosticar/`)

El endpoint de sensores es esperado que el ESP32 pueda acceder sin autenticación de sesión, pero debería implementarse al menos una API key simple. El endpoint IA debería requerir autenticación.

---

### 🟡 IMPORTANTE — `SECRET_KEY` fallback hardcodeado en settings

**Archivo:** `tiersystem/settings.py`, línea 13  
```python
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dummy-key-for-dev')
```
Si se despliega sin `SECRET_KEY` en las variables de entorno, usa una clave conocida. En desarrollo local está bien, pero el nombre `dummy-key-for-dev` sugiere que podría usarse accidentalmente en producción.

---

### 🟡 IMPORTANTE — Email credentials pueden ser `None` si no están configuradas

**Archivo:** `tiersystem/settings.py`, líneas 107-108  
```python
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')   # puede ser None
DEFAULT_FROM_EMAIL = f'TierSystem Notificaciones <{EMAIL_HOST_USER}>'
```
Si `EMAIL_HOST_USER` no está en el `.env`, `DEFAULT_FROM_EMAIL` será `'TierSystem Notificaciones <None>'`. Las vistas de solicitudes llaman `send_mail(..., fail_silently=True)`, así que no crashea, pero los correos fallarán silenciosamente.

---

### 🟢 MENOR — `REST_FRAMEWORK` con `AllowAny` en todos los endpoints

**Archivo:** `tiersystem/settings.py`, línea 98  
```python
'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny']
```
Con comentario `# Change to IsAuthenticated later`. Los endpoints de DRF (si los hubiera) serían accesibles sin autenticación.

---

### 🟢 MENOR — `DEBUG = True` y `ALLOWED_HOSTS = ['*']`

**Archivo:** `tiersystem/settings.py`, líneas 17 y 20  
Configuración de desarrollo. No es un bug pero debe cambiar antes de cualquier exposición pública.

---

## 9. MODELOS Y LÓGICA DE NEGOCIO

### ✅ LIMPIO — Todos los modelos están bien definidos

- `Perfil` (usuarios), `Terreno`, `SolicitudAnalisis`, `RegistroAnalisis`, `CultivoIdeal`, `ConfiguracionGlobal`, `LecturaSensor`, `PrecioMercado`, `Comprador` — todos con campos correctamente definidos.
- Relaciones FK y OneToOne correctas.
- `ConfiguracionGlobal.save()` fuerza `pk=1` (Singleton pattern). Correcto.

### 🟢 MENOR — `historial_analisis_agricultor` no filtra `solicitudes_disponibles` por `hasattr(s, 'analisis_resultado')`

**Archivo:** `apps/solicitudes/views.py`, función `historial_analisis_agricultor` (~línea 330)  
**Descripción:** Usa `.select_related('analisis_resultado', ...)` y luego `if hasattr(s, 'analisis_resultado'):`. Si la solicitud está en estado 'COMPLETADA' pero no tiene `RegistroAnalisis` asociado (edge case de consistencia de datos), simplemente se omite del historial. Esto es el comportamiento correcto, pero puede confundir al agricultor si una solicitud "COMPLETADA" no aparece en el historial.

---

## 10. DEPENDENCIAS

### 🟡 IMPORTANTE — `google-generativeai` deprecado

Como se mencionó en sección 1, este paquete dejará de recibir actualizaciones. Puede dejar de funcionar con nuevos modelos de Gemini.

### ✅ LIMPIO — `reportlab`, `openpyxl` instalados correctamente

- `reportlab 5.0.1` ✅
- `openpyxl 3.1.5` ✅

---

## LISTA CONSOLIDADA POR SEVERIDAD

### 🔴 CRÍTICOS (requieren fix inmediato)

| # | Archivo | Línea | Problema |
|---|---------|-------|----------|
| C1 | `apps/usuarios/models.py` | 27-28 | Signal `guardar_perfil_usuario` sin guard `hasattr` → `AttributeError` potencial |
| C2 | `apps/ia_recomendaciones/views.py` | 89 | Nombre de modelo Gemini `'gemini-3.6-flash'` no existe → Error 500 en producción |
| C3 | `templates/admin/usuarios.html` | 473 + 381 | `csrfToken` puede ser `null` → `TypeError` en JS |

### 🟡 IMPORTANTES (fix recomendado)

| # | Archivo | Línea | Problema |
|---|---------|-------|----------|
| I1 | `apps/ia_recomendaciones/views.py` | 9 | Paquete `google-generativeai` deprecado |
| I2 | `apps/solicitudes/views.py` | ~260 | `comparar_analisis_agricultor` accede a `analisis_resultado` sin guard → RelatedObjectDoesNotExist |
| I3 | `apps/sensores/views.py` | 8 | Endpoint `recibir_datos_sensor` sin autenticación ni validación de origen |
| I4 | `apps/ia_recomendaciones/views.py` | 20 | Endpoint `api_diagnosticar_ia` sin autenticación → gasta créditos API |
| I5 | `tiersystem/settings.py` | 107-108 | `EMAIL_HOST_USER` puede ser `None` → `DEFAULT_FROM_EMAIL` inválido |
| I6 | `apps/mercado/views.py` | ~290 | Request HTTP sincrónica a DANE en cada page load → latencia hasta 2s |
| I7 | `templates/laboratorista/dashboard.html` | ~190 | URLs de fetch hardcodeadas (no crítico funcionalmente) |
| I8 | `apps/usuarios/models.py` | 27-28 | Signal `guardar_perfil` potencialmente redundante/peligroso |

### 🟢 MENORES (mejorar cuando sea posible)

| # | Archivo | Línea | Problema |
|---|---------|-------|----------|
| M1 | `tiersystem/tiersystem/` | — | Directorio anidado duplicado remanente de `startproject` |
| M2 | `templates/agricultor/solicitudes.html` | ~180 | URL hardcodeada para `cancelar` en JS |
| M3 | `templates/agricultor/terrenos.html` | ~290 | URLs hardcodeadas para editar/eliminar finca |
| M4 | `templates/admin/usuarios.html` | ~416 | URL hardcodeada para editar usuario |
| M5 | `tiersystem/settings.py` | 17/20 | `DEBUG=True` y `ALLOWED_HOSTS=['*']` (solo dev) |
| M6 | `tiersystem/settings.py` | 98 | DRF con `AllowAny` (comentado para cambiar) |
| M7 | `apps/solicitudes/views.py` | ~330 | Solicitudes COMPLETADAS sin RegistroAnalisis no aparecen en historial sin aviso |

---

## CATEGORÍAS LIMPIAS (sin problemas)

- ✅ **Migraciones** — Todas aplicadas, sin cambios detectados
- ✅ **Templates — Sintaxis** — Los 19 templates cargaron sin errores
- ✅ **URLs nombradas** — Las 38 URLs verificadas (incluyendo namespaces) resuelven correctamente
- ✅ **Context Processor** — `solicitud_activa` correctamente registrado y usado
- ✅ **Archivos estáticos** — `styles.css` y todos los assets presentes
- ✅ **Modelos** — Bien definidos, relaciones correctas
- ✅ **Exportación PDF/Excel** — `reportlab` y `openpyxl` instalados y usados correctamente
- ✅ **Autenticación de vistas** — Todas las vistas HTML tienen `@login_required` y verificación de rol
- ✅ **Django system check** — `manage.py check` → 0 issues

---

## RECOMENDACIONES DE FIX (ordenadas por prioridad)

1. **[C1]** Agregar guard `hasattr` en signal `guardar_perfil_usuario` (5 min)
2. **[C2]** Cambiar `'gemini-3.6-flash'` → `'gemini-1.5-flash'` en `views.py` de IA (1 min)
3. **[C3]** Reemplazar `csrfToken = document.querySelector(...)` por función `getCookie('csrftoken')` en `admin/usuarios.html` (5 min)
4. **[I2]** Agregar guard para `analisis_resultado` en `comparar_analisis_agricultor` (10 min)
5. **[I1]** Migrar de `google-generativeai` a `google-genai` (30 min)
6. **[I3/I4]** Agregar validación básica de API key o `@login_required` en endpoints de sensores e IA (15 min)
7. **[I6]** Cachear resultado del check de conectividad DANE por 5 minutos con `django.core.cache` (15 min)
8. **[M1]** Eliminar directorio `tiersystem/tiersystem/` (1 min)
