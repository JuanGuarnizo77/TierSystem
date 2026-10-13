# Análisis Completo del Módulo Agricultor — TierSystem

**Proyecto:** TierSystem (Django 5.2)  
**Fecha de análisis:** Investigación estática del código fuente  
**Base de datos:** MySQL (Laragon, `tiersystem_db`, host `127.0.0.1:3306`)  
**Directorio raíz:** `c:\Users\punto\Desktop\tyersistem clon\tiersystem\`

---

## 1. Resumen Ejecutivo

El módulo agricultor **no es un único app de Django**, sino una sección funcional transversal distribuida entre cuatro apps (`apps/usuarios`, `apps/terrenos`, `apps/solicitudes`, `apps/mercado`) y el paquete `core/`. El agricultor interactúa con el sistema a través de un dashboard propio, con 6 secciones funcionales claramente separadas: gestión de fincas, solicitudes de análisis de suelo, historial con exportación, comparación de análisis, mercado/precios SIPSA y catálogo de cultivos. La autenticación y la redirección por rol la controla `apps/usuarios`. No existe `core/mixins.py` ni `core/permissions.py` con contenido: la verificación de rol se hace **manualmente en cada vista** con la guarda `request.user.perfil.rol != 'AGRICULTOR'`.

---

## 2. Mapa de Archivos del Módulo Agricultor

### 2.1 URLs raíz (`tiersystem/urls.py`)

| Prefijo URL | App incluida | Descripción |
|---|---|---|
| `''` | `apps.usuarios.urls` | Login, registro, perfil, logout |
| `''` | `core.urls` | Home, dashboards, catálogo cultivos |
| `agricultor/fincas/` | `apps.terrenos.urls` | CRUD de fincas/terrenos |
| `agricultor/solicitudes/` | `apps.solicitudes.urls_agricultor` | Solicitudes, historial, exportaciones |
| `mercado/` | `apps.mercado.urls` | Precios SIPSA y API AJAX |

> **Nota:** El archivo `tiersystem/tiersystem/urls.py` (la carpeta interna) está vacío (solo tiene `path('admin/', admin.site.urls)`). El archivo activo es `tiersystem/urls.py` (en el directorio raíz del proyecto, que es `tiersystem/`).

### 2.2 Archivo de configuración

| Archivo | Relevancia |
|---|---|
| `tiersystem/settings.py` | `ROOT_URLCONF = 'tiersystem.urls'`, DB MySQL, TEMPLATES apunta a `templates/`, apps registradas |

---

## 3. Modelos de Base de Datos

### 3.1 `apps/usuarios/models.py` — Modelo `Perfil`

```
Perfil
├── user         → OneToOneField(User)  [related_name='perfil']
├── rol          → CharField choices: AGRICULTOR | LABORATORISTA | ADMIN
└── telefono     → CharField (opcional)
```

- Extiende `django.contrib.auth.models.User` mediante OneToOneField.
- Se crea automáticamente vía **signals** `post_save` cuando se registra un `User`.
- El rol **por defecto es `AGRICULTOR`** (todo usuario nuevo es agricultor a menos que un admin cambie el rol).

### 3.2 `apps/terrenos/models.py` — Modelo `Terreno`

```
Terreno
├── agricultor           → ForeignKey(User)  [related_name='terrenos']
├── nombre               → CharField(100)
├── ubicacion            → CharField(255)  — vereda, municipio, etc.
├── hectareas            → DecimalField(8,2)
├── cultivo_principal    → CharField(100)  [null, blank]
├── coordenadas_poligono → TextField  [JSON string del polígono]
└── fecha_registro       → DateTimeField(auto_now_add=True)
```

- Un agricultor puede tener **múltiples terrenos** (FK → User).
- Las coordenadas del polígono se guardan como JSON texto libre (sin validación geoespacial).

### 3.3 `apps/solicitudes/models.py` — Modelo `SolicitudAnalisis`

```
SolicitudAnalisis
├── agricultor              → ForeignKey(User)  [related_name='solicitudes_creadas']
├── terreno                 → ForeignKey(Terreno)  [related_name='solicitudes']
├── laboratorista_asignado  → ForeignKey(User, null)  [related_name='solicitudes_asignadas']
├── estado                  → CharField choices: PENDIENTE|ASIGNADA|EN_PROCESO|COMPLETADA|RECHAZADA|CANCELADA
├── cultivo_deseado         → CharField(100)  default='No especificado'
├── modalidad               → CharField choices: VISITA|LLEVAR_MUESTRA
├── fecha_solicitud         → DateTimeField(auto_now_add=True)
├── fecha_visita            → DateField  [null, blank]
└── notas_agricultor        → TextField  [null, blank]
```

- **Regla de negocio clave:** Solo puede existir **una solicitud activa** por agricultor (estados PENDIENTE/ASIGNADA/EN_PROCESO) simultáneamente — validado en `crear_solicitud()`.
- El campo `analisis_resultado` es el `related_name` del OneToOneField en `RegistroAnalisis`.

### 3.4 `apps/analisis/models.py` — Modelo `RegistroAnalisis`

```
RegistroAnalisis
├── solicitud       → OneToOneField(SolicitudAnalisis)  [related_name='analisis_resultado']
├── humedad         → DecimalField(5,2)
├── temperatura     → DecimalField(5,2)
├── conductividad   → DecimalField(8,2)
├── ph              → DecimalField(4,2)
├── nitrogeno       → DecimalField(6,2)
├── fosforo         → DecimalField(6,2)
├── potasio         → DecimalField(6,2)
├── diagnostico_ia  → TextField  [JSON string del diagnóstico IA, null]
└── fecha_analisis  → DateTimeField(auto_now_add=True)
```

- Creado por el **Laboratorista** (no por el agricultor).
- El agricultor lo consume en modo lectura para ver resultados.

### 3.5 `apps/ia_recomendaciones/models.py` — Modelos `CultivoIdeal` y `ConfiguracionGlobal`

```
CultivoIdeal
├── nombre           → CharField(100, unique)
├── descripcion      → TextField [null]
└── [rangos_min/max] → FloatField: humedad, temperatura, conductividad, ph, nitrogeno, fosforo, potasio

ConfiguracionGlobal (singleton pk=1)
├── tiempo_espera_ia → IntegerField default=30
├── accion_fallo_ia  → choices: DB_LOCAL|CANCELAR
└── rango_[param]_[min|max] → FloatField para ph, n, p, k, humedad, ce, temp
```

- `CultivoIdeal` es la tabla que usa `_evaluar_parametros_agronomicos()` para comparar valores medidos con los rangos ideales.
- `ConfiguracionGlobal` es un singleton (se fuerza `pk=1` en `save()`).

### 3.6 `apps/mercado/models.py` — Modelos `ProductoMercado`, `PrecioMercado`, `Comprador`

```
ProductoMercado
├── vendedor             → ForeignKey(User)  [related_name='productos_venta']
├── nombre, descripcion, precio, cantidad_disponible
├── unidad_medida        → CharField(50)
├── fecha_publicacion    → DateTimeField(auto_now_add=True)
└── activo               → BooleanField(default=True)

PrecioMercado
├── cultivo_nombre, region, precio_promedio, precio_local
├── unidad, tendencia (Alza|Baja|Estable), variacion_porcentaje
├── fuente               → CharField(100) default='SIPSA / DANE'
└── fecha_actualizacion  → DateField(auto_now=True)

Comprador
├── nombre, tipo (Cooperativa, Plaza, Intermediario, Exportador)
├── municipio, contacto
├── cultivos_interes     → CharField(255)
├── precio_referencia    → CharField [null]
└── activo               → BooleanField
```

> **Importante:** Los modelos `PrecioMercado` y `Comprador` existen en la BD pero **no se usan** en las vistas actuales. La vista `precios_sipsa` opera con el diccionario estático `DATOS_MERCADO_HUILA` definido directamente en `apps/mercado/views.py`.

### 3.7 `apps/sensores/models.py` — Modelo `LecturaSensor`

```
LecturaSensor
├── humedad, temperatura, conductividad, ph, nitrogeno, fosforo, potasio → FloatField
└── timestamp → DateTimeField(auto_now_add=True)
```

- El agricultor no escribe en esta tabla; la lee indirectamente cuando el laboratorista registra el análisis.

---

## 4. Vistas y Funciones del Módulo Agricultor

### 4.1 `apps/usuarios/views.py`

| Función | URL name | Descripción |
|---|---|---|
| `login_view` | `login` | Autentica al usuario. Si es AGRICULTOR, redirige a `dashboard_agricultor`. |
| `register_view` | `registro` | Crea nuevo usuario con rol AGRICULTOR por defecto. |
| `perfil_view` | `perfil` | GET: renderiza `agricultor/perfil.html`. POST: actualiza `first_name`, `telefono` o cambia contraseña (action: `update_info` / `change_password`). |

### 4.2 `core/views.py`

| Función | URL name | Descripción |
|---|---|---|
| `home` | `home` | Redirect inteligente según rol. Para AGRICULTOR → `dashboard_agricultor`. |
| `dashboard_agricultor` | `dashboard_agricultor` | Dashboard principal. Carga: total terrenos, solicitud activa, total análisis completados, último análisis con `_evaluar_parametros_agronomicos()`. Renderiza `agricultor/dashboard.html`. |
| `catalogo_cultivos` | `catalogo_cultivos` | Carga la lista de 40 cultivos del Huila desde `core/cultivos_data.py` como JSON y renderiza `agricultor/cultivos.html`. |

### 4.3 `apps/terrenos/views.py`

| Función | URL completa | Método | Descripción |
|---|---|---|---|
| `mis_terrenos` | `GET /agricultor/fincas/` | GET | Lista todos los terrenos del agricultor. Renderiza `agricultor/terrenos.html`. |
| `crear_terreno` | `POST /agricultor/fincas/crear/` | POST | Crea un nuevo `Terreno`. Valida: nombre, ubicación, hectáreas (float). Retorna JSON. |
| `eliminar_terreno` | `POST /agricultor/fincas/eliminar/<id>/` | POST | Elimina terreno si pertenece al agricultor. Retorna JSON. |
| `editar_terreno` | `POST /agricultor/fincas/editar/<id>/` | POST | Actualiza todos los campos del terreno. Retorna JSON. |

### 4.4 `apps/solicitudes/views.py` — Sección Agricultor

| Función | URL completa | Descripción |
|---|---|---|
| `mis_solicitudes_agricultor` | `GET /agricultor/solicitudes/mis-solicitudes/` | Lista todas las solicitudes del agricultor con su terreno y resultado. También carga terrenos y cultivos para el formulario modal de creación. Renderiza `agricultor/solicitudes.html`. |
| `crear_solicitud` | `POST /agricultor/solicitudes/crear/` | Crea nueva `SolicitudAnalisis`. Valida que no exista solicitud activa previa. Campos: `terreno_id`, `cultivo_deseado`, `modalidad`, `notas`. |
| `cancelar_solicitud` | `POST /agricultor/solicitudes/cancelar/<id>/` | Cancela solicitud solo si está en estado `PENDIENTE`. |
| `resultado_detalle_agricultor` | `GET /agricultor/solicitudes/resultado/<id>/` | Muestra el detalle completo del análisis. Si no hay `analisis_resultado`, muestra banner de "análisis pendiente". Llama a `_evaluar_parametros_agronomicos()`. |
| `historial_analisis_agricultor` | `GET /agricultor/solicitudes/historial/` | Lista todas las solicitudes `COMPLETADA` con evaluación de compatibilidad calculada. Renderiza `agricultor/historial.html`. |
| `comparar_analisis_agricultor` | `GET /agricultor/solicitudes/comparar/` | Compara 2 análisis (por `?id1=&id2=`). Si hay menos de 2, muestra banner `insuficientes`. Renderiza `agricultor/comparar.html`. |
| `exportar_historial_pdf` | `GET /agricultor/solicitudes/exportar/pdf/` | Genera PDF con `reportlab` de todo el historial del agricultor. Descarga como archivo. |
| `exportar_historial_excel` | `GET /agricultor/solicitudes/exportar/excel/` | Genera `.xlsx` con `openpyxl`. Descarga como archivo. |
| `exportar_analisis_individual_pdf` | `GET /agricultor/solicitudes/resultado/<id>/pdf/` | Ficha técnica individual de un análisis en PDF. |

#### Función utilitaria clave: `_evaluar_parametros_agronomicos(analisis_obj, cultivo_nombre)`

- Busca el `CultivoIdeal` correspondiente en BD (búsqueda `icontains`).
- Evalúa los 7 parámetros: pH, N, P, K, Humedad, Conductividad, Temperatura.
- Por cada parámetro: determina estado (`Óptimo`/`Deficiente`/`Excesivo`), clase CSS, porcentaje de barra visual y recomendación de acción.
- Calcula `compatibilidad_calculada` (35% a 95% según parámetros óptimos).
- Devuelve un dict con `parametros`, `recomendaciones`, `compatibilidad`, `nivel_compatibilidad`, `color_compatibilidad`, `cultivos_alternativos`, y `consejo_general` (de IA si existe).
- Es llamada desde: `resultado_detalle_agricultor`, `historial_analisis_agricultor`, `comparar_analisis_agricultor`, `exportar_historial_pdf`, `exportar_historial_excel`, `exportar_analisis_individual_pdf`, y también desde `core/views.py::dashboard_agricultor`.

### 4.5 `apps/mercado/views.py`

| Función | URL completa | Descripción |
|---|---|---|
| `precios_sipsa` | `GET /mercado/` | Vista principal de precios. Usa el dict estático `DATOS_MERCADO_HUILA` con 9 cultivos (Maíz, Café, Cacao, Plátano, Frijol, Aguacate Hass, Papa, Tomate, Arroz). Intenta conectarse a la API real de DANE (`datos.gov.co`) para indicar estado online/offline. Renderiza `agricultor/mercado.html`. |
| `api_datos_cultivo_mercado` | `GET /mercado/api/cultivo/<nombre>/` | Retorna JSON con precios, historial y compradores para actualización AJAX al cambiar cultivo seleccionado. |

---

## 5. URLs Expuestas al Agricultor

### Módulo Usuarios / Autenticación

| URL | Nombre | Vista |
|---|---|---|
| `/login/` | `login` | `usuarios.views.login_view` |
| `/registro/` | `registro` | `usuarios.views.register_view` |
| `/perfil/` | `perfil` | `usuarios.views.perfil_view` |
| `/logout/` | `logout` | Django `LogoutView` → redirige a `home` |

### Core (Dashboard y Catálogo)

| URL | Nombre | Vista |
|---|---|---|
| `/` | `home` | `core.views.home` |
| `/agricultor/dashboard/` | `dashboard_agricultor` | `core.views.dashboard_agricultor` |
| `/agricultor/cultivos/` | `catalogo_cultivos` | `core.views.catalogo_cultivos` |

### Fincas (namespace: `terrenos`)

| URL | Nombre completo | Vista |
|---|---|---|
| `/agricultor/fincas/` | `terrenos:mis_terrenos` | `terrenos.views.mis_terrenos` |
| `/agricultor/fincas/crear/` | `terrenos:crear_terreno` | `terrenos.views.crear_terreno` |
| `/agricultor/fincas/eliminar/<id>/` | `terrenos:eliminar_terreno` | `terrenos.views.eliminar_terreno` |
| `/agricultor/fincas/editar/<id>/` | `terrenos:editar_terreno` | `terrenos.views.editar_terreno` |

### Solicitudes (namespace: `solicitudes_agricultor`)

| URL | Nombre completo | Vista |
|---|---|---|
| `/agricultor/solicitudes/mis-solicitudes/` | `solicitudes_agricultor:mis_solicitudes` | `solicitudes.views.mis_solicitudes_agricultor` |
| `/agricultor/solicitudes/crear/` | `solicitudes_agricultor:crear_solicitud` | `solicitudes.views.crear_solicitud` |
| `/agricultor/solicitudes/cancelar/<id>/` | `solicitudes_agricultor:cancelar_solicitud` | `solicitudes.views.cancelar_solicitud` |
| `/agricultor/solicitudes/resultado/<id>/` | `solicitudes_agricultor:resultado_detalle` | `solicitudes.views.resultado_detalle_agricultor` |
| `/agricultor/solicitudes/resultado/<id>/pdf/` | `solicitudes_agricultor:exportar_analisis_pdf` | `solicitudes.views.exportar_analisis_individual_pdf` |
| `/agricultor/solicitudes/historial/` | `solicitudes_agricultor:historial` | `solicitudes.views.historial_analisis_agricultor` |
| `/agricultor/solicitudes/comparar/` | `solicitudes_agricultor:comparar_analisis` | `solicitudes.views.comparar_analisis_agricultor` |
| `/agricultor/solicitudes/exportar/pdf/` | `solicitudes_agricultor:exportar_pdf` | `solicitudes.views.exportar_historial_pdf` |
| `/agricultor/solicitudes/exportar/excel/` | `solicitudes_agricultor:exportar_excel` | `solicitudes.views.exportar_historial_excel` |

### Mercado (namespace: `mercado`)

| URL | Nombre completo | Vista |
|---|---|---|
| `/mercado/` | `mercado:precios_sipsa` | `mercado.views.precios_sipsa` |
| `/mercado/api/cultivo/<nombre>/` | `mercado:api_datos_cultivo` | `mercado.views.api_datos_cultivo_mercado` |

---

## 6. Conexiones Entre Módulos (Dependencias)

```
apps/usuarios  ─────────────────────────────────────────────────────────
  └── Provee: User + Perfil (rol=AGRICULTOR)
        │
        ├──→ core/views.py (dashboard_agricultor)
        │       ├──→ apps.terrenos.models.Terreno
        │       ├──→ apps.solicitudes.models.SolicitudAnalisis
        │       └──→ apps.solicitudes.views._evaluar_parametros_agronomicos()
        │
        ├──→ apps/terrenos/views.py
        │       └──→ apps.terrenos.models.Terreno
        │
        ├──→ apps/solicitudes/views.py (sección agricultor)
        │       ├──→ apps.terrenos.models.Terreno
        │       ├──→ apps.analisis.models.RegistroAnalisis
        │       └──→ apps.ia_recomendaciones.models.CultivoIdeal, ConfiguracionGlobal
        │
        └──→ apps/mercado/views.py
                └──→ [Dict estático DATOS_MERCADO_HUILA, no BD]
                └──→ requests → https://www.datos.gov.co (API externa, timeout 2s)
```

### Grafo de importaciones cruzadas entre apps

| App origen | Importa de |
|---|---|
| `core/views.py` | `apps.terrenos.models`, `apps.solicitudes.models`, `apps.solicitudes.views`, `apps.analisis.models`, `apps.ia_recomendaciones.models`, `apps.sensores.models` |
| `apps/solicitudes/views.py` | `apps.terrenos.models`, `apps.analisis.models`, `apps.ia_recomendaciones.models` |
| `apps/analisis/models.py` | `apps.solicitudes.models` |
| `apps/solicitudes/models.py` | `apps.terrenos.models` |
| `apps/mercado/views.py` | Ninguna app interna (standalone) |
| `apps/terrenos/views.py` | Ninguna app interna |
| `apps/usuarios/views.py` | Ninguna app interna directa |

---

## 7. Mixins y Permisos

### Estado actual

- **`core/mixins.py`**: archivo vacío (sin contenido).
- **`core/permissions.py`**: archivo vacío (sin contenido).

### Mecanismo de control de acceso real

Cada vista usa una guarda manual al inicio:

```python
# Patrón 1: redirect silencioso
if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
    return redirect('home')

# Patrón 2: error JSON para endpoints AJAX
if not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'AGRICULTOR':
    return JsonResponse({'error': 'No autorizado'}, status=403)
```

- El decorador `@login_required(login_url='login')` se usa en todas las vistas del módulo agricultor.
- No hay uso de `UserPassesTestMixin`, `PermissionRequiredMixin`, ni permisos de Django (`django.contrib.auth`).
- No hay grupos de permisos de Django configurados.
- La verificación `hasattr(request.user, 'perfil')` es necesaria porque el signal podría fallar (caso edge: usuario sin perfil creado).

---

## 8. Templates HTML del Módulo Agricultor

| Template | Ruta | Descripción |
|---|---|---|
| `base_dashboard.html` | `templates/agricultor/` | Layout principal con sidebar, dark mode, Tailwind CDN, FontAwesome, SweetAlert2. Extienden todos los demás. |
| `dashboard.html` | `templates/agricultor/` | Inicio: estadísticas rápidas (último análisis, solicitud activa, total terrenos, total análisis), accesos rápidos. |
| `terrenos.html` | `templates/agricultor/` | Lista de fincas con mapa de polígonos, modal AJAX para crear/editar/eliminar. |
| `solicitudes.html` | `templates/agricultor/` | Lista de solicitudes con modal de creación (selector de terreno y cultivo). |
| `historial.html` | `templates/agricultor/` | Historial completo con badges de compatibilidad y botones de exportación PDF/Excel. |
| `resultado_detalle.html` | `templates/agricultor/` | Detalle del análisis: 7 parámetros con barras, estado, recomendaciones, cultivos alternativos. |
| `comparar.html` | `templates/agricultor/` | Tabla comparativa de 2 análisis parámetro a parámetro con indicadores de tendencia. |
| `mercado.html` | `templates/agricultor/` | Precios SIPSA: gráfica de historial 6 meses, tabla de compradores, indicador online/offline. |
| `mi_tienda.html` | `templates/agricultor/` | Gestión de productos del agricultor en el mercado (CRUD de `ProductoMercado`). |
| `cultivos.html` | `templates/agricultor/` | Catálogo de 40 cultivos del Huila (renderizado con JS desde JSON). |
| `perfil.html` | `templates/agricultor/` | Edición de nombre, teléfono y contraseña. Dos acciones POST vía AJAX. |
| `precios_sipsa.html` | `templates/agricultor/` | (Alias de `mercado.html` — la vista `precios_sipsa` renderiza `agricultor/mercado.html`) |
| `login.html` | `templates/usuarios/` | Página de login con diseño split-screen y descripción del sistema. |
| `register.html` | `templates/usuarios/` | Formulario de registro de agricultor. |

### Stack de Frontend

- **CSS:** Tailwind CSS vía CDN (`cdn.tailwindcss.com`), con configuración `darkMode: 'class'`, colores personalizados (`primary: #0a4d3c`, `accent: #10b981`).
- **Iconos:** FontAwesome 6.4 + Tabler Icons (CDN).
- **Modales/Alertas:** SweetAlert2 (CDN).
- **Dark Mode:** Toggle con `localStorage` + clase `dark` en `<html>`.
- **CSS propio:** `static/css/styles.css`.

---

## 9. Flujo Completo del Agricultor

```
1. INICIO
   └── GET /  →  core.views.home
       └── Si autenticado y rol=AGRICULTOR → redirect 'dashboard_agricultor'
       └── Si no autenticado → renderiza home.html (página pública)

2. REGISTRO (nuevo agricultor)
   └── GET/POST /registro/  →  usuarios.views.register_view
       ├── Form: RegistroForm (username, email, password, password_confirm)
       ├── Crea User → Signal crea Perfil con rol='AGRICULTOR'
       └── Login automático → redirect 'dashboard_agricultor'

3. LOGIN (agricultor existente)
   └── GET/POST /login/  →  usuarios.views.login_view
       ├── Form: Django AuthenticationForm
       └── Si rol=AGRICULTOR → redirect 'dashboard_agricultor'

4. DASHBOARD
   └── GET /agricultor/dashboard/  →  core.views.dashboard_agricultor
       ├── Consulta: Terreno.objects.filter(agricultor=request.user)
       ├── Consulta: SolicitudAnalisis activa (PENDIENTE|ASIGNADA|EN_PROCESO)
       ├── Consulta: últimas solicitudes COMPLETADA
       ├── Evalúa último análisis con _evaluar_parametros_agronomicos()
       └── Context: total_terrenos, solicitud_activa, total_analisis, ultimo_analisis, evaluacion_ultimo, terrenos_recientes

5. GESTIÓN DE FINCAS
   └── GET /agricultor/fincas/  →  mis_terrenos
       └── Terreno.objects.filter(agricultor=user).order_by('-fecha_registro')
   └── POST /agricultor/fincas/crear/  →  crear_terreno  [JSON response]
   └── POST /agricultor/fincas/editar/<id>/  →  editar_terreno  [JSON response]
   └── POST /agricultor/fincas/eliminar/<id>/  →  eliminar_terreno  [JSON response]

6. SOLICITUD DE ANÁLISIS
   └── GET /agricultor/solicitudes/mis-solicitudes/  →  mis_solicitudes_agricultor
       ├── Lista solicitudes + terrenos + cultivos (para modal)
   └── POST /agricultor/solicitudes/crear/  →  crear_solicitud
       ├── Valida: no hay solicitud activa previa
       ├── Valida: terreno pertenece al agricultor
       └── Crea SolicitudAnalisis (estado='PENDIENTE')
   └── POST /agricultor/solicitudes/cancelar/<id>/  →  cancelar_solicitud
       └── Solo si estado='PENDIENTE'

   [EL LABORATORISTA ACEPTA, PROCESA Y COMPLETA LA SOLICITUD]
   [Envía correo al agricultor en cada cambio de estado]

7. VER RESULTADO
   └── GET /agricultor/solicitudes/resultado/<id>/
       ├── Verifica que solicitud.analisis_resultado exista
       ├── Llama _evaluar_parametros_agronomicos(analisis, cultivo_deseado)
       └── Renderiza con 7 parámetros evaluados, recomendaciones, compatibilidad

8. HISTORIAL Y COMPARACIÓN
   └── GET /agricultor/solicitudes/historial/  →  historial_analisis_agricultor
   └── GET /agricultor/solicitudes/comparar/?id1=X&id2=Y  →  comparar_analisis_agricultor
   └── GET /agricultor/solicitudes/exportar/pdf/  →  exportar_historial_pdf (reportlab)
   └── GET /agricultor/solicitudes/exportar/excel/  →  exportar_historial_excel (openpyxl)
   └── GET /agricultor/solicitudes/resultado/<id>/pdf/  →  exportar_analisis_individual_pdf

9. MERCADO
   └── GET /mercado/  →  precios_sipsa
       ├── Carga DATOS_MERCADO_HUILA (dict estático, 9 cultivos)
       ├── Intenta GET a datos.gov.co para estado online/offline (timeout 2s)
       └── Renderiza agricultor/mercado.html con precios, historial, compradores

10. CATÁLOGO DE CULTIVOS
    └── GET /agricultor/cultivos/  →  catalogo_cultivos
        └── Carga CULTIVOS_HUILA (40 cultivos, core/cultivos_data.py) como JSON

11. PERFIL
    └── GET/POST /perfil/  →  perfil_view
        ├── POST action='update_info': actualiza first_name, telefono
        └── POST action='change_password': cambia contraseña, mantiene sesión activa
```

---

## 10. Observaciones y Problemas Detectados

### 🔴 Problemas Críticos

1. **`tiersystem/tiersystem/urls.py` incompleto:** El archivo de URLs en la carpeta interna `tiersystem/tiersystem/` solo tiene `path('admin/', admin.site.urls)`. El archivo funcional está en `tiersystem/urls.py`. Esto es confuso por la doble carpeta, pero el `settings.py` activo (`tiersystem/settings.py`) apunta correctamente a `ROOT_URLCONF = 'tiersystem.urls'`.

2. **`mi_tienda.html` referencia `{% url 'mercado:publico' %}`** que no existe en `apps/mercado/urls.py`. Solo existen `mercado:precios_sipsa` y `mercado:api_datos_cultivo`. Esto causará `NoReverseMatch` al cargar la vista de mi tienda.

3. **`exportar_historial_pdf` usa `datetime.now()` sin importar `datetime`:** La línea `datetime.now().strftime(...)` fallará con `NameError` porque no hay un `from datetime import datetime` al inicio de `apps/solicitudes/views.py` (solo se importa `io`). Debe añadirse el import.

4. **Modelos `PrecioMercado` y `Comprador` en BD pero sin uso en vistas:** Los datos del mercado provienen de un diccionario hardcodeado en Python, no de la base de datos. Esto significa que el admin no puede actualizar precios desde el panel de administración.

### 🟡 Problemas Importantes

5. **`core/mixins.py` y `core/permissions.py` vacíos:** Los archivos existen pero no tienen contenido. La intención fue crear mixins reutilizables pero esto no se completó. La consecuencia es que cada vista repite la misma guarda de rol (~40 veces en el proyecto), violando DRY.

6. **Sin validación CSRF en endpoints JSON:** Los endpoints que usan `request.POST` tienen protección CSRF de Django activa (correcto), pero los que usan `request.body` con JSON (en `core/views.py` para el admin) hacen `json.loads(request.body)` sin verificar `Content-Type`. No afecta al agricultor directamente.

7. **Coordenadas de polígono sin validación:** El campo `coordenadas_poligono` acepta cualquier texto. No hay validación de formato JSON en el servidor.

8. **`solicitudes.views` sección laboratorista y agricultor en el mismo archivo:** El archivo `apps/solicitudes/views.py` mezcla vistas del laboratorista y del agricultor. Esto dificulta el mantenimiento.

### 🟢 Buenas Prácticas Detectadas

9. **Regla de negocio de solicitud única:** La validación de "solo una solicitud activa" es correcta y coherente.

10. **Notificaciones por correo:** El laboratorista puede disparar correos al agricultor al aceptar/rechazar solicitudes (con `fail_silently=True` para no romper el flujo).

11. **Namespaces de URL:** Los tres módulos del agricultor (`terrenos`, `solicitudes_agricultor`, `mercado`) usan `app_name` correctamente, evitando conflictos de nombres.

---

## 11. Recomendaciones

| Prioridad | Acción |
|---|---|
| 🔴 Alta | Añadir `from datetime import datetime` en `apps/solicitudes/views.py` (línea ~370 del código) para corregir el error en exportación PDF del historial. |
| 🔴 Alta | Añadir la URL `mercado:publico` en `apps/mercado/urls.py` o corregir el template `mi_tienda.html` para apuntar a `mercado:precios_sipsa`. |
| 🟡 Media | Implementar `core/mixins.py` con un `AgricultorRequiredMixin` o decorador `@agricultor_required` para eliminar la duplicación de la guarda de rol. |
| 🟡 Media | Conectar las vistas del mercado a los modelos `PrecioMercado` y `Comprador` de la BD para que los datos sean administrables. |
| 🟢 Baja | Separar `apps/solicitudes/views.py` en dos archivos: `views_agricultor.py` y `views_laboratorista.py`. |
| 🟢 Baja | Añadir validación JSON del lado servidor para el campo `coordenadas_poligono` en `crear_terreno` y `editar_terreno`. |

---

*Reporte generado por análisis estático del código fuente. No se ejecutó ningún servidor ni se modificó ningún archivo.*
