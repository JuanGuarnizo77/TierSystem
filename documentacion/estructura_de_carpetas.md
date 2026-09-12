TierSystem-Django/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── tiersystem/                 # Configuración global del proyecto
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py                 # urls raíz, aquí solo se hace include() de cada app
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/                       # TODAS las apps de Django, una por dominio funcional
│   ├── __init__.py
│   ├── usuarios/                # login, registro, roles, perfiles
│   ├── terrenos/                 # terrenos y cultivos del agricultor
│   ├── solicitudes/              # ciclo de vida: pendiente→aceptada→en proceso→finalizada
│   ├── sensores/                 # ESP32, lecturas, 7 parámetros (RQF-4, prioridad actual)
│   ├── analisis/                  # validación de rangos, perfil promedio de suelo
│   ├── ia_recomendaciones/       # integración IA externa (fase posterior)
│   └── mercado/                   # SIPSA/DANE (fase posterior)
│
├── core/                        # Código compartido entre apps
│   ├── __init__.py
│   ├── permissions.py           # permisos por rol (agricultor/laboratorista/admin)
│   ├── mixins.py
│   └── utils.py
│
├── templates/                   # Templates globales (layout compartido)
│   ├── base.html
│   └── includes/                # navbar, footer, etc.
│
├── static/
│   ├── css/
│   ├── js/
│   └── img/
│
└── media/                       # archivos subidos (fotos de terrenos, etc.)