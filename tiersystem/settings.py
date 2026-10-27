"""
Configuración Global del Proyecto Django: TierSystem.
======================================================
Define todos los ajustes arquitectónicos, de seguridad, persistencia relacional,
comunicación asíncrona, internacionalización y servicios de autenticación del sistema.

Componentes clave:
  - Carga dinámica de variables de entorno mediante `python-dotenv`.
  - Soporte dual de motores de base de datos (MySQL para entornos de producción/staging
    y SQLite3 para entornos de desarrollo local rápido).
  - Configuración de Django REST Framework con autenticación de tokens JWT (`SimpleJWT`).
  - Documentación de API OpenAPI 3.0 mediante `drf-spectacular`.
  - Zona horaria de Colombia ('America/Bogota') e idioma español colombiano ('es-co').
  - Gestor de correo electrónico transaccional SMTP con fallback a consola.
  - Llave de autenticación compartida para telemetría de sensores IoT de campo.
"""

import os
from pathlib import Path
from datetime import timedelta

# Carga de variables de entorno desde el archivo .env (si existe)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Directorio raíz del proyecto (donde reside manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Clave secreta criptográfica para firma de sesiones, tokens CSRF y cookies seguras
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dummy-key-for-dev')

# Bandera de depuración: True en desarrollo local; debe ser False en entornos de producción
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Dominios y direcciones IP permitidas para recibir peticiones HTTP
if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,tiersystem.pythonanywhere.com').split(',')

# Orígenes de confianza para validación contra ataques CSRF (Cross-Site Request Forgery)
CSRF_TRUSTED_ORIGINS = [
    'https://tiersystem.pythonanywhere.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000'
]


# =============================================================================
# DEFINICIÓN DE APLICACIONES (INSTALLED_APPS)
# =============================================================================

INSTALLED_APPS = [
    # Módulos centrales provistos por Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Paquetes y extensiones de terceros
    'rest_framework',                  # Framework para construcción de APIs RESTful
    'rest_framework_simplejwt',        # Autenticación basada en JSON Web Tokens (JWT)
    'drf_spectacular',                 # Generación de especificación OpenAPI 3.0 / Swagger

    # Aplicaciones locales del dominio TierSystem
    'api',                             # Controladores y endpoints de la API REST móvil
    'apps.cultivos',                   # Catálogo agronómico y parámetros óptimos de cultivo
    'apps.usuarios',                   # Cuentas, roles y perfiles extendidos
    'apps.terrenos',                   # Cartografía y registro de predios y fincas
    'apps.solicitudes',                # Ciclo de vida de solicitudes de análisis edafológico
    'apps.sensores',                   # Telemetría e ingesta de datos de sondas IoT
    'apps.analisis',                   # Cálculos de nutrientes, interpretación y reportes
    'apps.ia_recomendaciones',         # Motor de IA dual (Google Gemini + algoritmo local)
    'apps.mercado',                    # Directorio de compradores y comercialización Huila
    'apps.sipsa',                      # Integración con series de precios DANE / SIPSA
    'core',                            # Vistas centrales, diseño PWA y panel administrativo
]


# =============================================================================
# CADENA DE INTERMEDIARIOS (MIDDLEWARE)
# =============================================================================

MIDDLEWARE = [
    # Protección de cabeceras HTTP y redirecciones SSL seguras
    'django.middleware.security.SecurityMiddleware',
    # Gestión de sesiones persistentes basadas en cookies
    'django.contrib.sessions.middleware.SessionMiddleware',
    # Normalización de URLs y manejo de agentes de usuario
    'django.middleware.common.CommonMiddleware',
    # Protección obligatoria contra falsificación de peticiones en sitios cruzados
    'django.middleware.csrf.CsrfViewMiddleware',
    # Inyección del usuario autenticado en request.user
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Notificaciones temporales al usuario mediante el framework de mensajes
    'django.contrib.messages.middleware.MessageMiddleware',
    # Mitigación contra ataques de secuestro de clics (Clickjacking)
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Configuración del archivo de rutas raíz
ROOT_URLCONF = 'tiersystem.urls'

# Configuración del motor de renderizado de plantillas HTML
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Context processor personalizado para inyectar la solicitud activa en el panel
                'core.context_processors.solicitud_activa',
            ],
        },
    },
]

# Punto de entrada para servidores WSGI tradicionales (Gunicorn, uWSGI, PythonAnywhere)
WSGI_APPLICATION = 'tiersystem.wsgi.application'


# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS (SOPORTE DUAL: MYSQL / SQLITE3)
# =============================================================================

DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite').lower()

if DB_ENGINE == 'mysql':
    # Conexión relacional para servidor MySQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'tiersystem_db'),
            'USER': os.getenv('DB_USER', 'root'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '3306'),
        }
    }
else:
    # Conexión local predeterminada basada en archivo SQLite embebido
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# =============================================================================
# VALIDACIÓN DE COMPLEJIDAD DE CONTRASEÑAS
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =============================================================================
# INTERNACIONALIZACIÓN Y ZONA HORARIA
# =============================================================================

# Idioma español con localización para Colombia
LANGUAGE_CODE = 'es-co'

# Zona horaria oficial de la República de Colombia (UTC-5)
TIME_ZONE = 'America/Bogota'

# Activar motor de traducción de cadenas
USE_I18N = True

# Activar gestión de fechas y horas conscientes de huso horario (Timezone-Aware)
USE_TZ = True


# =============================================================================
# ARCHIVOS ESTÁTICOS Y MULTIMEDIA
# =============================================================================

# URL relativa pública para servir recursos estáticos (CSS, JS, imágenes de interfaz)
STATIC_URL = 'static/'

# Directorio de recopilación para producción al ejecutar `collectstatic`
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Directorios de búsqueda de recursos estáticos durante el desarrollo
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Configuración para archivos cargados por los usuarios (firmas, fotos de lotes)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Tipo de clave primaria automática predeterminado para nuevos modelos (Big Integer de 64 bits)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# CONFIGURACIÓN DE DJANGO REST FRAMEWORK (DRF)
# =============================================================================

REST_FRAMEWORK = {
    # Esquemas de autenticación admitidos en los endpoints de la API
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # Por defecto, todos los endpoints requieren sesión o token válido
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Generador de esquema OpenAPI 3.0 para documentación interactiva
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Metadatos del catálogo OpenAPI para Swagger UI / Redoc
SPECTACULAR_SETTINGS = {
    'TITLE': 'TierSystem API',
    'DESCRIPTION': 'API REST para la plataforma de análisis de suelos TierSystem - Huila, Colombia',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Ajustes de tiempo de vida y rotación para JSON Web Tokens (JWT)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),     # Duración óptima para jornadas de trabajo de campo
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),     # Permite refrescar credenciales sin requerir re-login mensual
    'ROTATE_REFRESH_TOKENS': True,                    # Emite un nuevo refresh token en cada renovación
    'BLACKLIST_AFTER_ROTATION': False,                # No requiere tabla de lista negra en la base de datos
    'AUTH_HEADER_TYPES': ('Bearer',),                 # Encabezado estándar Authorization: Bearer <token>
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}


# =============================================================================
# CONFIGURACIÓN DE NOTIFICACIONES POR CORREO ELECTRÓNICO (EMAIL)
# =============================================================================

_email_user = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_USER = _email_user
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    # Servidor SMTP de producción (Google Gmail con contraseña de aplicación)
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
else:
    # Fallback seguro para desarrollo: imprime los enlaces y tokens de confirmación en la consola
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Dirección de correo predeterminada del remitente para notificaciones automáticas
DEFAULT_FROM_EMAIL = f'TierSystem Notificaciones <{_email_user}>' if _email_user else 'TierSystem Notificaciones <noreply@tiersystem.co>'

# Llave secreta para autenticación de peticiones POST originadas por los microcontroladores ESP32
SENSOR_API_KEY = os.getenv('SENSOR_API_KEY', 'tiersystem-sensor-key-dev')