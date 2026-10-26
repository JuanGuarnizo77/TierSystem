# API Móvil — TierSystem

## ¿Qué es esto?

Este documento explica cómo está construida y cómo funciona la conexión entre la aplicación móvil Flutter y el backend Django de TierSystem. Está escrito para que cualquier desarrollador del equipo pueda entender el sistema sin necesidad de revisar el código directamente.

---

## Visión general

TierSystem tiene dos interfaces: la plataforma web y la aplicación móvil construida en Flutter. Ambas usan el mismo servidor Django y la misma base de datos. La web usa sesiones y templates HTML, mientras que la app móvil se comunica exclusivamente mediante una API REST que devuelve datos en formato JSON.

Toda la API móvil vive bajo el prefijo `/api/v1/` para no interferir con las rutas de la web.

---

## Autenticación

El sistema usa JWT (JSON Web Token) a través de `djangorestframework-simplejwt`.

* **Access Token**: Duración de 8 horas. Demuestra que el usuario está autenticado y se envía en el encabezado `Authorization: Bearer <token>`.
* **Refresh Token**: Duración de 30 días. Permite renovar el access token sin forzar al usuario a iniciar sesión nuevamente.

Flutter guarda los tokens en el dispositivo usando `shared_preferences`. Al abrir la app, revisa si hay un token válido y el rol guardado para redirigir directamente al panel correspondiente.

---

## Estructura Modular de la API (`api/`)

La API REST v1 cubre los flujos completos tanto del **Agricultor** como del **Laboratorista**, además de la autenticación JWT:

```text
api/
├── permissions.py              # Permisos reutilizables (IsAgricultor, IsLaboratorista, IsAdmin)
├── urls.py                     # Enrutador principal de la API (/api/v1/)
│
├── auth/                       # Autenticación y Perfil
│   ├── serializers.py          # Serializers de Usuario, Perfil y Registro
│   ├── views.py                # LoginView, Registro, Me y Logout
│   └── urls.py                 # Rutas bajo /api/v1/auth/
│
├── agricultor/                 # Módulo de Agricultor
│   ├── serializers.py          # TerrenoSerializer, SolicitudSerializer, etc.
│   ├── views_perfil.py         # Consulta de perfil y cambio de contraseña
│   ├── views_terrenos.py       # CRUD completo de predios / parcelas (ViewSet)
│   ├── views_solicitudes.py    # CRUD y seguimiento de órdenes de análisis (ViewSet)
│   ├── views_resultados.py     # Historial de análisis, detalle y comparativa diferencial
│   ├── views_cultivos.py       # Catálogo maestro de cultivos del Huila
│   ├── views_mercado.py        # Cotizaciones mayoristas SIPSA/DANE y actualización
│   ├── views_reportes.py       # Reportes de analítica agropecuaria y tendencias
│   └── urls.py                 # Rutas bajo /api/v1/agricultor/
│
└── laboratorista/              # Módulo de Laboratorista (Operativo en Campo)
    ├── views_dashboard.py      # Métricas y contadores de solicitudes activas y finalizadas
    ├── views_solicitudes.py    # Banco de pendientes, asignadas, aceptar y rechazar órdenes
    ├── views_muestreo.py       # Sensor ESP32 en vivo, cuadrícula, guardado de puntos 3D y consolidación
    ├── views_historial.py      # Historial de estudios de suelo procesados y detalle
    ├── views_consulta.py       # Consulta interactiva de compatibilidad por cultivo asistida por IA
    └── urls.py                 # Rutas bajo /api/v1/laboratorista/
```

---

## Catálogo de Endpoints Implementados

### 1. Autenticación (`/api/v1/auth/`)
* **POST `/api/v1/auth/login/`**
  * Body: `{ "username": "...", "password": "..." }`
  * Devuelve: `access`, `refresh` y el objeto `user` con su rol y datos de perfil.
* **POST `/api/v1/auth/registro/`**
  * Body: `{ "username", "email", "first_name", "last_name", "password", "password2", "telefono" }`
  * Registra automáticamente con rol `AGRICULTOR` y devuelve tokens para inicio de sesión inmediato.
* **GET `/api/v1/auth/me/`**
  * Header: `Authorization: Bearer <access_token>`
  * Devuelve los datos del perfil actualizados del usuario autenticado.
* **POST `/api/v1/auth/refresh/`**
  * Body: `{ "refresh": "<refresh_token>" }`
  * Devuelve un nuevo `access` token.
* **POST `/api/v1/auth/logout/`**
  * Body: `{ "refresh": "<refresh_token>" }`

### 2. Agricultor (`/api/v1/agricultor/`)
* **`GET|POST /api/v1/agricultor/terrenos/`**: Listado de fincas propias o radicación de nuevo predio con GeoJSON y hectáreas.
* **`GET|PUT|PATCH|DELETE /api/v1/agricultor/terrenos/<id>/`**: Consulta detallada, actualización o eliminación de finca.
* **`GET|POST /api/v1/agricultor/solicitudes/`**: Listado de solicitudes o creación de nueva solicitud (aplica regla US-0009 de máx. 1 activa).
* **`GET|DELETE /api/v1/agricultor/solicitudes/<id>/`**: Consulta o cancelación de solicitud (solo si está en `PENDIENTE`).
* **`GET|PUT /api/v1/agricultor/perfil/`**: Consulta y actualización de datos biográficos y contacto del productor.
* **`POST /api/v1/agricultor/perfil/password/`**: Cambio de contraseña con verificación de clave anterior.
* **`GET /api/v1/agricultor/historial/`**: Historial completo de análisis edafológicos finalizados.
* **`GET /api/v1/agricultor/resultados/<solicitud_id>/`**: Dictamen técnico con balance de nutrientes y recomendaciones.
* **`GET /api/v1/agricultor/comparar/?id1=<id>&id2=<id>`**: Comparador nutricional y de compatibilidad entre dos lotes.
* **`GET /api/v1/agricultor/cultivos/`**: Catálogo oficial de especies agrícolas adaptadas al Huila.
* **`GET /api/v1/agricultor/mercado/precios/`**: Cotizaciones mayoristas del DANE/SIPSA para Huila y tendencias.
* **`POST /api/v1/agricultor/mercado/actualizar/`**: Disparador para refrescar precios del boletín oficial.
* **`GET /api/v1/agricultor/reportes/`**: Listado de reportes de mercado y comportamiento de precios.
* **`GET /api/v1/agricultor/reportes/<cultivo_id>/`**: Análisis específico de rentabilidad y precios por producto.

### 3. Laboratorista (`/api/v1/laboratorista/`)
* **`GET /api/v1/laboratorista/dashboard/`**: Métricas de órdenes de servicio, tareas asignadas y análisis completados.
* **`GET /api/v1/laboratorista/solicitudes/pendientes/`**: Bandeja global de solicitudes pendientes de asignación.
* **`GET /api/v1/laboratorista/solicitudes/banco/`**: Alias del banco general de solicitudes de los agricultores.
* **`GET /api/v1/laboratorista/solicitudes/mis-tareas/`**: Órdenes asignadas específicamente al laboratorista autenticado.
* **`POST /api/v1/laboratorista/solicitudes/<id>/aceptar/`**: Aceptación de visita con fijación de fecha y envío de correo SMTP.
* **`POST /api/v1/laboratorista/solicitudes/<id>/rechazar/`**: Rechazo justificado con retorno de la orden al banco de pendientes.
* **`GET /api/v1/laboratorista/muestreo/sensor/`**: Lectura estabilizada en tiempo real del sensor ESP32 (Modbus RTU / RS485).
* **`GET /api/v1/laboratorista/muestreo/<solicitud_id>/`**: Cuadrícula de puntos de muestreo calculada según hectáreas del lote.
* **`POST /api/v1/laboratorista/muestreo/puntos/<punto_id>/guardar/`**: Persistencia de perforación física 3D (lat, lon, alt, NPK, pH).
* **`POST /api/v1/laboratorista/muestreo/<solicitud_id>/generar/`**: Consolidación de medias, ejecución del motor edafológico y finalización de la orden.
* **`GET /api/v1/laboratorista/historial/`**: Historial de estudios de suelo completados por el técnico.
* **`GET /api/v1/laboratorista/resultados/<solicitud_id>/`**: Consulta del dictamen agronómico completo y plan de fertilización.
* **`POST /api/v1/laboratorista/resultados/<solicitud_id>/consulta-cultivo/`**: Consulta agronómica interactiva asistida por Google Gemini o fallback heurístico.


---

## Seguridad y `.gitignore`

* **Secretos:** El archivo `.env` y certificados (`*.pem`, `*.key`) están ignorados por Git para evitar fugas de credenciales.
* **Entornos virtuales:** Se ignoran tanto `venv/` como `venv_linux/`.
* **Base de datos:** `db.sqlite3` y volcados `.sql` no se rastrean en el repositorio.
* **Esquemas:** `tiersystem_schema.json` se mantiene fuera del repositorio si contiene estructuras locales transitorias.

---

## Herramientas de Desarrollo y Pruebas

* **Swagger UI:** Accesible en `http://localhost:8000/api/v1/docs/` para interactuar y probar cualquier endpoint con autorización Bearer Token.
* **OpenAPI Schema:** Generado automáticamente en `http://localhost:8000/api/v1/schema/`.
