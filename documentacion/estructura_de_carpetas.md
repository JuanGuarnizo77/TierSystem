# Estructura del Proyecto TierSystem

Estructura de directorios y organización modular de la plataforma web y API móvil TierSystem:

```text
TierSystem/
├── manage.py                          # Gestor de comandos de Django
├── requirements.txt                   # Dependencias Python (Django, DRF, JWT, reportlab, openpyxl, etc.)
├── seed_cultivos.py                   # Script de inicialización del catálogo ampliado de cultivos
├── .env.example                       # Plantilla de variables de entorno (SMTP, DB, etc.)
├── .gitignore                         # Archivos y carpetas ignorados por Git
├── db.sqlite3                         # Base de datos local (desarrollo/pruebas)
│
├── tiersystem/                        # Configuración global del proyecto
│   ├── __init__.py
│   ├── settings.py                    # Configuración general, apps, auth JWT, email backend y DB
│   ├── urls.py                        # Enrutamiento raíz con include() hacia cada app, sipsa y api móvil
│   ├── asgi.py
│   └── wsgi.py
│
├── api/                               # Capa REST API para la aplicación móvil (Flutter)
│   ├── permissions.py                 # Permisos basados en roles (IsAgricultor, IsLaboratorista, IsAdmin)
│   ├── urls.py                        # Enrutador principal de la API (/api/v1/)
│   ├── auth/                          # Autenticación JWT y gestión de identidad
│   │   ├── serializers.py             # Serializadores de usuario y perfil
│   │   ├── views.py                   # LoginView, Registro, Me y Logout
│   │   └── urls.py                    # Rutas bajo /api/v1/auth/
│   └── agricultor/                    # Endpoints para el rol de Agricultor
│       ├── serializers.py             # Serializadores de fincas y solicitudes
│       ├── views_perfil.py            # Consulta y actualización de perfil del agricultor
│       ├── views_terrenos.py          # CRUD de fincas / parcelas
│       ├── views_solicitudes.py       # Flujo de solicitudes de análisis
│       └── urls.py                    # Rutas bajo /api/v1/agricultor/
│
├── apps/                              # Aplicaciones modulares por dominio funcional (Web)
│   ├── __init__.py
│   ├── usuarios/                      # Login, registro, auth views, perfiles (Admin, Lab, Agri)
│   ├── terrenos/                      # CRUD de predios y hectáreas del agricultor
│   ├── solicitudes/                   # Ciclo de vida: Pendiente → Aceptada → En proceso → Finalizada
│   ├── sensores/                      # API endpoint para ESP32 (/api/lecturas/), telemetría y hardware
│   ├── analisis/                      # Rangos agronómicos, evaluación local y detalle técnico
│   ├── ia_recomendaciones/            # Cliente API REST externa de IA y motor de fallback
│   ├── mercado/                       # Analítica de mercado, directorio de compradores y cotizaciones
│   └── sipsa/                         # Integración con DANE/SIPSA, reportes de precios y predicciones
│       ├── admin.py
│       ├── models.py                  # Modelos de precios de referencia y series de tiempo
│       ├── prediccion.py              # Algoritmo de proyección y estimación de tendencias
│       ├── views.py                   # Vistas del dashboard de precios y reportes
│       └── urls.py                    # Rutas bajo /agricultor/sipsa/
│
├── templates/                         # Plantillas HTML con diseño responsivo Tailwind
│   ├── base.html                      # Layout base principal
│   ├── home.html                      # Landing page del sistema
│   │
│   ├── usuarios/                      # Vistas de autenticación y seguridad
│   │   ├── login.html                 # Pantalla de acceso con SweetAlert2
│   │   ├── registro.html              # Registro de agricultor
│   │   ├── password_reset_form.html   # Solicitud de recuperación de contraseña
│   │   ├── password_reset_done.html   # Notificación de correo enviado
│   │   ├── password_reset_confirm.html# Ingreso de nueva clave con validación en vivo
│   │   ├── password_reset_complete.html# Confirmación de clave restablecida con éxito
│   │   ├── password_reset_email.html  # Cuerpo HTML del correo electrónico
│   │   └── password_reset_subject.txt # Asunto del correo de recuperación
│   │
│   ├── admin/                         # Panel integral de administración
│   │   ├── base_admin.html            # Layout administrativo con acceso a perfil en topbar
│   │   ├── dashboard.html             # Resumen de métricas generales
│   │   ├── usuarios.html              # Gestión de laboratoristas y agricultores
│   │   ├── supervision.html           # Supervisión de análisis y exportación PDF/Excel
│   │   ├── hardware.html              # Diagnóstico y estado del sensor ESP32
│   │   ├── cultivos.html              # Catálogo CRUD de cultivos con búsqueda en vivo
│   │   ├── rangos.html                # Configuración de rangos agronómicos de referencia
│   │   ├── ia_config.html             # Políticas de timeout y fallback de IA
│   │   ├── laboratoristas.html        # Auditoría y actividad de laboratoristas
│   │   └── perfil.html                # Edición de perfil y clave del Administrador
│   │
│   ├── laboratorista/                 # Panel operativo en campo para el Laboratorista
│   │   ├── base_dashboard.html        # Layout con estado de conexión y acceso a perfil en topbar
│   │   ├── dashboard.html             # Agenda y solicitudes asignadas
│   │   ├── captura.html               # Interfaz de conexión ESP32 y captura de suelo
│   │   ├── toma_muestras.html         # Captura de puntos y perfil promedio de muestreo
│   │   ├── historial.html             # Historial de análisis con botones de exportación PDF/Excel
│   │   └── perfil.html                # Edición de perfil y clave del Laboratorista
│   │
│   ├── agricultor/                    # Panel de autogestión para el Agricultor
│   │   ├── base_dashboard.html        # Layout con barra de navegación y perfil en topbar
│   │   ├── dashboard.html             # Panel principal con accesos rápidos
│   │   ├── terrenos.html              # Registro y listado de predios
│   │   ├── solicitudes.html           # Creación y seguimiento de solicitudes
│   │   ├── historial.html             # Histórico de análisis y dictámenes
│   │   ├── resultado_detalle.html     # Detalle completo de resultados de análisis
│   │   ├── comparar.html              # Comparativa entre análisis de suelo
│   │   ├── cultivos.html              # Catálogo de cultivos recomendados con búsqueda
│   │   ├── mercado.html               # Cotizaciones SIPSA, gráficos y compradores
│   │   ├── precios_sipsa.html         # Vista detallada de precios históricos del DANE
│   │   ├── mi_tienda.html             # Gestión de ofertas del agricultor
│   │   └── perfil.html                # Edición de perfil y clave del Agricultor
│   │
│   └── sipsa/                         # Módulo de inteligencia de mercado SIPSA/DANE
│       ├── dashboard.html             # Dashboard general de precios agrícolas de la región Huila
│       └── detalle_cultivo.html       # Tendencias, predicción estadística y comportamiento por producto
│
├── static/                            # Recursos estáticos locales (Soporte Offline)
│   ├── css/                           # Hojas de estilo y Tailwind CSS compilado localmente
│   ├── fontawesome/                   # Iconografía FontAwesome local (sin dependencia CDN)
│   ├── js/                            # Scripts de validación, notificaciones y gráficas
│   ├── img/                           # Logotipos, avatar predeterminado e iconografía
│   └── manifest.json                  # Manifiesto PWA para instalación en móviles
│
└── documentacion/                     # Documentación técnica y de ingeniería de software
    ├── TierSystem_Funciones_del_Sistema.md # Resumen funcional, arquitectura y backlog
    ├── funcionalidadesactores.md      # Matriz de trazabilidad US-0001 a US-0049 y detalle por rol
    ├── estructura_de_carpetas.md      # Mapa de directorios y componentes del sistema
    ├── api_movil.md                   # Especificación técnica de la API REST para Flutter y JWT
    ├── conexion.md                    # Código C++ para ESP32, pines RS485 y Modbus RTU
    ├── ajustes_entorno_local.md       # Guía de configuración y arranque en Linux
    └── historias de usuario/          # Archivo de especificación oficial en Excel / CSV
```