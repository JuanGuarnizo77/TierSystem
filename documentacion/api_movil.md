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

Actualmente la API está enfocada en el flujo completo del **Agricultor** y la autenticación:

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
└── agricultor/                 # Módulo de Agricultor
    ├── serializers.py          # TerrenoSerializer, SolicitudSerializer (con validación de fincas propias)
    ├── views_terrenos.py       # CRUD de fincas / parcelas
    ├── views_solicitudes.py    # Flujo de solicitudes de análisis
    └── urls.py                 # Rutas bajo /api/v1/agricultor/ (y alias directo en raíz de API)
```

*(El módulo de `laboratorista/` se implementará en una fase posterior cuando se integren las pantallas de toma de muestras y el sensor ESP32).*

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

### 2. Agricultor (`/api/v1/agricultor/` o directo `/api/v1/`)
* **`GET /api/v1/agricultor/terrenos/`**: Lista de fincas pertenecientes al agricultor autenticado.
* **`POST /api/v1/agricultor/terrenos/`**: Registra una nueva finca (valida hectáreas > 0).
* **`GET|PUT|DELETE /api/v1/agricultor/terrenos/<id>/`**: Consulta, edita o elimina una finca propia.
* **`GET /api/v1/agricultor/solicitudes/`**: Lista el historial de solicitudes de análisis del agricultor.
* **`POST /api/v1/agricultor/solicitudes/`**: Crea una nueva solicitud (valida que solo tenga una activa a la vez y que la finca le pertenezca).
* **`DELETE /api/v1/agricultor/solicitudes/<id>/`**: Cancela una solicitud (únicamente si está en estado `PENDIENTE`).

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
