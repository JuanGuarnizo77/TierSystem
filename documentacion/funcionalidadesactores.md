# TierSystem — Funciones del Sistema por Actor y Matriz de Trazabilidad

> **Documento de referencia funcional y técnico**, basado en el SRS (Documento de Requerimientos de Software) de TierSystem v1.0 y el catálogo oficial de Historias de Usuario (US-0001 a US-0049).  
> **Última actualización:** Octubre 2026.  
> **Estado general del sistema:**
> - ✅ **Módulo de Administrador:** **100% Implementado** (Cuentas de Laboratoristas y Agricultores, supervisión integral con reportes exportables a PDF y Excel, monitoreo de hardware, CRUD de cultivos, rangos agronómicos de referencia, fallback/timeout de IA y trazabilidad de actividad).
> - ✅ **Autenticación y Seguridad (US-0001 a US-0005):** Registro de Agricultores, Login multirrol con validación y alertas, Cierre de sesión seguro, Recuperación de contraseña vía email/token de un solo uso con validación de seguridad en vivo (US-0004), y Gestión de Perfil Personal para los 3 roles con cambio de credenciales y acceso directo en barra superior (US-0005).
> - ✅ **Módulo de Inteligencia de Mercado (US-0013 a US-0017):** Precios SIPSA/DANE, histórico trimestral, tendencias de mercado y directorio de compradores regionales.
> - ✅ **Gestión de Terrenos y Solicitudes de Agricultor (US-0006 a US-0010):** CRUD de terrenos, creación de solicitudes con validación de unicidad activa y cancelación asistida.
> - ✅ **Operativa del Laboratorista y Captura Sensor (US-0021 a US-0025, US-0028 a US-0032):** Gestión de solicitudes, conexión ESP32/RS485, captura de 7 parámetros de suelo, motor de análisis con fallback local y entrega de resultados al Agricultor.
> - ✅ **Soporte Offline y Estilos:** Integración local de Tailwind CSS y FontAwesome en `static/`, eliminando dependencias de CDN en campo, con almacenamiento local en IndexedDB / Dexie.js (`db.js`).
> - ✅ **Muestreo en Campo, Comparativas y Exportación (US-0011, US-0012, US-0026, US-0027, US-0033):** Cuadrícula de 5 a 20 puntos según área con coordenadas 3D (lat, lon, altitud), cálculo de medias y perfil consolidado, comparador nutricional diferencial y exportación oficial a PDF y Excel.

---

## 1. Contexto general del sistema

TierSystem es una plataforma web para análisis de suelo en campo, dirigida a agricultores del departamento del Huila. El flujo central del sistema es el siguiente:

1. El **Agricultor** crea una solicitud de análisis seleccionando uno de sus terrenos registrados y el cultivo deseado.
2. El **Laboratorista** recibe la solicitud en su bandeja de trabajo, la acepta, se traslada al terreno, enlaza el módulo de hardware **ESP32**, y realiza la captura de datos del suelo mediante la sonda multiparamétrica.
3. El sistema valida los datos capturados y calcula el **perfil del suelo**, enviándolo al **Servicio de IA** (o al motor de inferencia local si se encuentra en zona sin cobertura).
4. El motor analítico determina el **porcentaje de compatibilidad**, evalúa los 7 parámetros agronómicos frente a los rangos ideales del cultivo, genera recomendaciones de enmienda/fertilización y sugiere cultivos alternativos cuando la compatibilidad es deficiente (<50%).
5. El Laboratorista valida el dictamen y lo **comparte con el Agricultor**, cerrando la solicitud como Finalizada.
6. En paralelo, el Agricultor cuenta con un módulo de **inteligencia de mercado** (SIPSA/DANE) para consultar precios actualizados, variaciones históricas y compradores regionales.

Todo el flujo operativo está diseñado para soportar trabajo **offline** en campo, sincronizando transacciones al recuperar conectividad.

---

## 2. Actores del sistema

| Actor | Tipo | Rol principal | Estado de Implementación |
|---|---|---|---|
| **Administrador** | Usuario de gestión | Administra usuarios, supervisa análisis, exporta reportes (PDF/Excel), vigila hardware, configura rangos agronómicos y fallback de IA. | **100% Completado** ✅ |
| **Agricultor** | Usuario final | Registra terrenos, crea solicitudes de análisis, consulta dictámenes técnicos, revisa historial, comparativas y mercado. | **100% Completado** ✅ |
| **Laboratorista** | Usuario operativo | Atiende solicitudes, opera el sensor ESP32 en campo, muestreo 3D por puntos, consolida y entrega análisis. | **100% Completado** ✅ |
| **Sensor (ESP32 + RS485)** | Actor externo hardware | Captura los 7 parámetros físicos y químicos del suelo y los transmite vía HTTP/WiFi o Bluetooth. | **100% Integrado** ✅ |
| **Servicio de IA (API)** | Actor externo software | Procesa el perfil de suelo, calcula compatibilidad, genera recomendaciones y cultivos alternativos. | **100% Integrado** (con motor local de respaldo) ✅ |

---

## 3. Matriz de Trazabilidad de Historias de Usuario (US-0001 a US-0049)

A continuación se detalla el estado actual de cada una de las 49 Historias de Usuario del catálogo oficial de TierSystem:

| ID | Historia de Usuario | Actor | Estado | Módulo / Componentes de Código |
|---|---|---|---|---|
| **US-0001** | Registro de cuenta personal por cuenta propia | Agricultor | ✅ Implementado | `apps/usuarios/views.py` (`registro_agricultor`), formulario con activación inmediata. |
| **US-0002** | Inicio de sesión seguro con credenciales | Todos los roles | ✅ Implementado | `apps/usuarios/views.py` (`login_view`), redirección automática por rol. |
| **US-0003** | Cierre de sesión seguro | Todos los roles | 🟡 Parcial | Escenario 1 (Manual) ✅ implementado (`logout_view`). Escenario 2 (Inactividad) ⏳ pendiente. |
| **US-0004** | Recuperación de contraseña vía email con token seguro | Todos los roles | ✅ Implementado | `apps/usuarios/urls.py`, vistas `auth_views`, plantillas SaaS `templates/usuarios/password_reset_*`. |
| **US-0005** | Consulta y edición de perfil personal y cambio de contraseña | Todos los roles | ✅ Implementado | `apps/usuarios/views.py` (`perfil_admin`, `perfil_laboratorista`, `perfil_agricultor`), Bento Grid UI y acceso topbar. |
| **US-0006** | Consulta de listado de terrenos registrados | Agricultor | ✅ Implementado | `apps/terrenos/views.py` (`lista_terrenos`). |
| **US-0007** | Registro de terrenos con nombre y área (m² / ha) | Agricultor | ✅ Implementado | `apps/terrenos/views.py` (`crear_terreno`), validaciones numéricas y de duplicidad. |
| **US-0008** | Edición y eliminación de terrenos con confirmación | Agricultor | ✅ Implementado | `apps/terrenos/views.py` (`editar_terreno`, `eliminar_terreno`), modal de borrado en cascada. |
| **US-0009** | Creación de solicitud de análisis de suelo | Agricultor | ✅ Implementado | `apps/solicitudes/views.py` (`crear_solicitud`), regla de máximo 1 solicitud activa. |
| **US-0010** | Consulta de estado y cancelación de solicitud activa | Agricultor | ✅ Implementado | `apps/solicitudes/views.py` (`detalle_solicitud_agricultor`, `cancelar_solicitud` en estado Pendiente). |
| **US-0011** | Consulta de historial de análisis y comparador | Agricultor | ✅ Implementado | `apps/solicitudes/views.py` (`comparar_analisis_agricultor`), `templates/agricultor/comparar.html` y `/api/v1/agricultor/comparar/`. |
| **US-0012** | Exportación de historial de análisis a PDF / Excel | Agricultor | ✅ Implementado | `apps/solicitudes/views.py` (`exportar_historial_pdf`, `exportar_historial_excel`), con renderizado ReportLab y openpyxl. |
| **US-0013** | Consulta de precio actual de mercado (SIPSA/DANE) | Agricultor | ✅ Implementado | `apps/mercado/views.py` (`mercado_precios`), cotización regional y fecha de corte. |
| **US-0014** | Historial de variaciones de precios de los últimos 3 meses | Agricultor | ✅ Implementado | `apps/mercado/views.py`, series cronológicas y visualización gráfica. |
| **US-0015** | Tendencias de mercado (al alza, estable, a la baja) | Agricultor | ✅ Implementado | `apps/mercado/views.py`, indicadores semafóricos de variación porcentual. |
| **US-0016** | Directorio de compradores activos en la región | Agricultor | ✅ Implementado | `apps/mercado/views.py`, intermediarios, cooperativas y plazas de mercado. |
| **US-0017** | Selector dinámico de cultivo en módulo de mercado | Agricultor | ✅ Implementado | `apps/mercado/views.py`, recarga dinámica de analítica por cultivo. |
| **US-0018** | Registro de nuevas cuentas de Laboratoristas por Admin | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_crear_laboratorista`), cuenta creada en estado inactivo. |
| **US-0019** | Activación y desactivación de cuentas de Laboratoristas | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_toggle_laboratorista`), control de acceso instantáneo. |
| **US-0020** | Eliminación permanente de cuentas de usuarios | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_eliminar_usuario`), confirmación estricta y borrado total. |
| **US-0021** | Consulta de solicitudes de análisis pendientes | Laboratorista | ✅ Implementado | `apps/solicitudes/views.py` (`solicitudes_laboratorista`), visualización de terreno y cultivo. |
| **US-0022** | Aceptación o rechazo de solicitudes de análisis | Laboratorista | ✅ Implementado | `apps/solicitudes/views.py` (`aceptar_solicitud`, `rechazar_solicitud`), límite de 1 activa. |
| **US-0023** | Actualización de estados del ciclo de la solicitud | Laboratorista | ✅ Implementado | `apps/solicitudes/views.py` (Pendiente → Aceptada → En proceso → Finalizada). |
| **US-0024** | Conexión con sensor ESP32 y verificación de estado operativo | Laboratorista | ✅ Implementado | `apps/sensores/views.py`, semáforo de conectividad y batería antes de muestreo. |
| **US-0025** | Supervisión de captura de datos del suelo en tiempo real | Laboratorista | ✅ Implementado | `apps/sensores/views.py`, recepción de los 7 parámetros y validación técnica. |
| **US-0026** | Visualización y registro de puntos de muestreo (1 a 5) | Laboratorista | ✅ Implementado | `templates/laboratorista/toma_muestras.html`, `api/laboratorista/views_muestreo.py` con cuadrícula de 5 a 20 puntos según área y GPS 3D. |
| **US-0027** | Cálculo del perfil promedio del suelo entre puntos tomados | Laboratorista | ✅ Implementado | `api/laboratorista/views_muestreo.py` (`generar_analisis_view`), consolidación estadística de medias y cierre. |
| **US-0028** | Consulta de parámetros agronómicos ideales del cultivo | Laboratorista | ✅ Implementado | `apps/analisis/views.py`, consulta contra base local o servicio de IA. |
| **US-0029** | Consulta de resultados emitidos por el motor de IA | Laboratorista | ✅ Implementado | `apps/ia_recomendaciones/views.py` y `apps/analisis/views.py`. |
| **US-0030** | Visualización de resultado integral en pantalla unificada | Laboratorista | ✅ Implementado | `templates/analisis/detalle.html`, porcentaje de compatibilidad y semáforos. |
| **US-0031** | Entrega de resultados al Agricultor y cierre de solicitud | Laboratorista | ✅ Implementado | `apps/solicitudes/views.py` (`compartir_analisis`), transición a Finalizada. |
| **US-0032** | Operación offline, motor local y sincronización | Laboratorista | ✅ Implementado | Almacenamiento local, motor de reglas agronómicas y etiqueta de dictamen local. |
| **US-0033** | Consulta de historial de análisis del Laboratorista | Laboratorista | ✅ Implementado | `templates/laboratorista/historial.html`, `api/laboratorista/views_historial.py` con historial cronológico y consulta de dictámenes. |
| **US-0034** | Consulta global de análisis registrados en el sistema | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_supervision`), tabla completa sin restricciones. |
| **US-0035** | Generación de reportes filtrados y exportación PDF/Excel | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_exportar_pdf`, `admin_exportar_excel`), filtros por fecha, usuario y cultivo. |
| **US-0036** | Supervisión del estado del sensor y hardware en tiempo real | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_hardware`), estado de batería, enlace y última lectura. |
| **US-0037** | Gestión de base de datos de cultivos (CRUD) | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_cultivos`), creación, edición y eliminación de cultivos. |
| **US-0038** | Configuración de rangos agronómicos de referencia | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_rangos`), ajuste de umbrales para los 7 parámetros. |
| **US-0039** | Configuración de políticas de fallback y timeout de IA | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_ia_config`), timeout en segundos y alternancia a motor local. |
| **US-0040** | Auditoría y consulta de actividad de Laboratoristas | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_laboratoristas_actividad`), métricas de atención y trabajo en curso. |
| **US-0041** | Notificación de estado operativo del sensor | Sensor (ESP32) | ✅ Implementado | Firmware en C++, transmisión de heartbeat y estado de batería. |
| **US-0042** | Captura de parámetros físicos ante comando del operador | Sensor (ESP32) | ✅ Implementado | Firmware en C++, activación de ciclo de medición de electrodos. |
| **US-0043** | Lectura Modbus RTU de sonda RS485 | Sensor (ESP32) | ✅ Implementado | Comunicación serie sobre pines DI/DE/RE/RO a 9600 baudios. |
| **US-0044** | Transmisión de lecturas al backend vía WiFi / HTTP | Sensor (ESP32) | ✅ Implementado | Petición `POST /api/lecturas/` con carga JSON de 7 parámetros. |
| **US-0045** | Recepción de lecturas por parte del servicio de IA | Servicio de IA | ✅ Implementado | `apps/ia_recomendaciones/service.py`, parseo y validación de payload. |
| **US-0046** | Normalización y preparación de datos del suelo | Servicio de IA | ✅ Implementado | Validación contra límites físicos y preparación de vector de variables. |
| **US-0047** | Cálculo de compatibilidad agronómica con el cultivo | Servicio de IA | ✅ Implementado | Algoritmo de distancia ponderada contra perfil agronómico ideal. |
| **US-0048** | Generación de planes de enmienda y cultivos alternativos | Servicio de IA | ✅ Implementado | Generación de dosificaciones correctivas y alternativas cuando score < 50%. |
| **US-0049** | Emisión del dictamen consolidado y confirmación | Servicio de IA | ✅ Implementado | Retorno de estructura con porcentaje, semáforos, recomendaciones y metadata. |

---

## 4. Agricultor — Funciones en detalle

El Agricultor es el usuario productor agropecuario. Su interfaz prioriza la facilidad de uso, legibilidad en pantallas móviles o tablets y retroalimentación inmediata.

### 4.1 Cuenta, sesión y perfil (US-0001 a US-0005)
- **Registro de cuenta (US-0001):** Formulario con nombre de usuario, teléfono de contacto y contraseña. La cuenta se activa de forma instantánea al registrarse sin requerir validación manual, redirigiendo de inmediato al panel principal.
- **Inicio de sesión (US-0002):** Acceso seguro con credenciales y protección contra ataques de fuerza bruta.
- **Cierre de sesión (US-0003):** Cierre manual desde la barra superior (`logout_view`).
- **Recuperación de contraseña (US-0004):** Flujo completo con envío de correo seguro, token criptográfico temporal y validación interactiva de robustez de contraseña (mínimo 8 caracteres, números, letras y no similitud con datos personales).
- **Perfil personal (US-0005):** Vista Bento Card (`templates/agricultor/perfil.html`) con edición de nombre, apellidos, correo, teléfono y formulario de cambio de clave con verificación en tiempo real. Accesible desde el avatar superior derecho del dashboard.

### 4.2 Gestión de terrenos (US-0006 a US-0008)
- **Consulta de terrenos (US-0006):** Listado visual de predios con nombre, área expresada en hectáreas o m², y accesos directos a gestión.
- **Registro de predios (US-0007):** Formulario para registrar terrenos validando que el área sea numérica estrictamente positiva y evitando nombres duplicados.
- **Edición y eliminación (US-0008):** Formulario de modificación de datos y modal de eliminación permanente con advertencia de borrado en cascada de los análisis históricos vinculados.

### 4.3 Solicitudes de análisis de suelo (US-0009 y US-0010)
- **Creación de solicitud (US-0009):** Selección de terreno propio, selección del cultivo objetivo del catálogo, y modalidad de entrega (llevar muestra al punto o visita del laboratorista a campo).
  - *Regla de negocio estricta:* Solo se admite **1 solicitud activa por Agricultor** (en estado Pendiente, Aceptada o En proceso).
- **Seguimiento y cancelación (US-0010):** Visualización del estado actual con línea de tiempo. El Agricultor puede **cancelar** la solicitud únicamente si permanece en estado **Pendiente**.

### 4.4 Resultados, historial y comparativa (US-0011, US-0012, US-0030)
- **Consulta de resultados:** Porcentaje global de compatibilidad (Alta ≥75%, Media 50-74%, Baja <50%), clasificación semafórica de los 7 parámetros (🟢 Óptimo, 🟡 Deficiente, 🔴 Excesivo), recomendaciones de enmienda y cultivos alternativos sugeridos.
- **Historial (US-0011):** Lista cronológica de análisis finalizados con etiqueta distintiva de "Generado en modo local" para los efectuados sin conexión.
- **Comparador de análisis (US-0011 - Escenarios 4-5):** *(⏳ Pendiente)* Comparación de dos análisis seleccionados para visualizar evoluciones del suelo tras enmiendas.
- **Exportación de historial (US-0012):** *(⏳ Pendiente)* Descarga del historial en formato PDF o Excel.

### 4.5 Inteligencia de mercado (US-0013 a US-0017)
- **Cotización actual (US-0013):** Consulta de precios promedio por producto basados en SIPSA/DANE con fecha de última actualización.
- **Histórico trimestral (US-0014):** Visualización de la evolución del precio en los últimos 3 meses mediante gráficos de tendencia.
- **Indicadores de tendencia (US-0015):** Detección automática de comportamiento alcista, bajista o estable.
- **Compradores zonales (US-0016):** Directorio de comercializadores, cooperativas agrarias y centrales de abasto locales con contacto y ubicación.
- **Selector de cultivo (US-0017):** Cambio instantáneo del cultivo analizado en el tablero de mercado.

---

## 5. Administrador — Funciones en detalle (100% Implementado)

El Administrador tiene el control total sobre la gobernanza de usuarios, el catálogo de cultivos, los rangos de tolerancia del hardware, la supervisión de análisis y la auditoría operativa.

### 5.1 Gestión de usuarios (US-0018 a US-0020)
- **Registro de Laboratoristas (US-0018):** Formulario administrativo para enrolar técnicos de laboratorio. Las cuentas se inicializan inactivas por defecto.
- **Activación y suspensión (US-0019):** Conmutador interactivo para activar o desactivar laboratoristas instantáneamente sin eliminar sus registros ni historial.
- **Eliminación permanente (US-0020):** Modal de confirmación crítica para depuración irreversible de cuentas de laboratoristas o agricultores.

### 5.2 Supervisión y reportes avanzados (US-0034 y US-0035)
- **Auditoría global de análisis (US-0034):** Tablero consolidado de todos los análisis generados en la plataforma, con filtros dinámicos por agricultor, laboratorista, fecha y cultivo.
- **Exportación de reportes (US-0035):** Generación y descarga directa de informes técnicos en **PDF** (diseño imprimible formal) y en **Excel (.xlsx)** con desglose detallado de los 7 parámetros de suelo.

### 5.3 Hardware y configuración del sistema (US-0036 a US-0040)
- **Monitoreo de hardware (US-0036):** Tablero de diagnóstico del sensor ESP32, nivel de batería, estado del módulo RS485, calidad de señal y timestamp de última lectura recibida.
- **Catálogo de cultivos (US-0037):** CRUD completo de cultivos agrícolas, configurando sus requerimientos ideales (pH, N, P, K, Humedad, CE, Temperatura).
- **Rangos agronómicos de referencia (US-0038):** Ajuste de los umbrales mínimos y máximos admisibles para la calibración del sensor y del motor de análisis offline.
- **Políticas de tolerancia a fallos de IA (US-0039):** Configuración del timeout de espera de la API externa y directiva de contingencia (fallback automático al motor local de reglas o suspensión y alerta).
- **Actividad de Laboratoristas (US-0040):** Métricas de desempeño, número de solicitudes atendidas, visitas en campo activas y tiempos de respuesta.

---

## 6. Laboratorista — Funciones en detalle

El Laboratorista es el actor técnico que opera en campo directamente sobre el terreno del agricultor.

### 6.1 Gestión de solicitudes operativas (US-0021 a US-0023)
- **Bandeja de solicitudes (US-0021):** Visualización de solicitudes pendientes con información del agricultor, predio, tamaño y cultivo a sembrar.
- **Aceptación / Rechazo (US-0022):** Decisión sobre la solicitud. Al aceptar, pasa a estado `Aceptada` y se asocia a su agenda de trabajo.
  - *Regla clave:* El laboratorista solo puede tener **1 solicitud activa en proceso simultáneamente**.
- **Avance de estados (US-0023):** Transición formal de la solicitud a `En proceso` al arribar al terreno y a `Finalizada` al compartir el dictamen.

### 6.2 Captura de datos con sensor ESP32 (US-0024, US-0025, US-0041 a US-0044)
- **Verificación de conexión (US-0024):** Reconocimiento del sensor en red local WiFi o Bluetooth; semáforo verde de enlace activo y nivel de batería adecuado.
- **Captura multiparamétrica (US-0025):** Disparo de la lectura en campo. La sonda RS485 captura los 7 parámetros agronómicos:
  1. pH (acidez/alcalinidad del suelo)
  2. Nitrógeno (N en mg/kg)
  3. Fósforo (P en mg/kg)
  4. Potasio (K en mg/kg)
  5. Humedad relativa (%)
  6. Conductividad Eléctrica (CE en µS/cm o dS/m)
  7. Temperatura del suelo (°C)
- **Validación técnica:** El backend comprueba que ningún valor esté fuera de la física operativa del sensor (ej. pH < 0 o > 14).

### 6.3 Puntos de muestreo y cálculo de promedios (US-0026 y US-0027 — ⏳ En Backlog)
- **Guía de puntos (US-0026):** Algoritmo que sugiere entre 1 y 5 puntos de toma según el área total del terreno (ej. muestreo en zig-zag) y permite registrar cada punto capturado.
- **Consolidación promedio (US-0027):** Agregación estadística de los puntos individuales tomados para conformar el perfil representativo del predio antes del cálculo analítico.

### 6.4 Análisis de compatibilidad y entrega (US-0028 a US-0032)
- **Evaluación agronómica:** Consulta de parámetros ideales (US-0028), inferencia mediante IA o motor local (US-0029) y despliegue del dictamen unificado (US-0030).
- **Entrega de resultados (US-0031):** Compartición formal con el agricultor; finalización de la solicitud y habilitación para tomar un nuevo servicio.
- **Modo offline resiliente (US-0032):** El laboratorista cuenta con caché de cultivos y rangos en su dispositivo; puede dictaminar sin internet con el motor local y sincronizar cuando recupere señal.

---

## 7. Arquitectura de Hardware y Protocolo de Comunicación

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FLUJO DE DATOS EN CAMPO                         │
├─────────────────┐          Modbus RTU          ┌───────────────────────┤
│  Sonda NPK/pH   │ ───────────────────────────> │     Módulo ESP32      │
│  7 Parámetros   │        (RS485 / UART2)       │  (WiFi / Bluetooth)   │
└─────────────────┘                              └──────────┬────────────┘
                                                            │
                                                   HTTP POST / JSON
                                                   (o caché local)
                                                            │
                                                            ▼
                                                 ┌───────────────────────┐
                                                 │   Backend Django      │
                                                 │   (API /sensores/)    │
                                                 └──────────┬────────────┘
                                                            │
                                  ┌─────────────────────────┴─────────────────────────┐
                             (Online)                                             (Offline)
                                  ▼                                                   ▼
                       ┌───────────────────────┐                           ┌─────────────────────┐
                       │    Servicio de IA     │                           │     Motor Local     │
                       │   (API Externa REST)  │                           │  (Reglas de Rangos) │
                       └───────────────────────┘                           └─────────────────────┘
```

- **Sonda:** Sensor integrado 7 en 1 con transceptor RS485 industrial.
- **ESP32:** DevKit V4 con convertidor TTL-RS485 (`RO`=GPIO 5, `DI`=GPIO 2, `DE`=GPIO 15, `RE`=GPIO 13) operando a 9600 baudios.
- **Endpoint Backend:** `POST /api/lecturas/` con cuerpo JSON validado contra rangos agronómicos.

---

## 8. Plan de Trabajo Restante (Backlog Priorizado)

Con el módulo del Administrador completado al 100%, la recuperación de contraseña y el perfil unificado en producción, las tareas restantes para completar el 100% de todo el sistema son:

1. **Sprint 1 (Laboratorista en Campo):**
   - Implementar la guía y contador visual de 1 a 5 puntos de muestreo en terreno (**US-0026**).
   - Implementar el cálculo del perfil promedio ponderado a partir de los puntos capturados (**US-0027**).
2. **Sprint 2 (Historial y Comparativas):**
   - Implementar la vista comparativa lado a lado de dos análisis en el historial del Agricultor (**US-0011 - Escenarios 4 y 5**) y del Laboratorista (**US-0033 - Escenario 2**).
   - Implementar la exportación del historial del Agricultor en PDF y Excel (**US-0012**).
3. **Sprint 3 (Seguridad y Pulido):**
   - Implementar middleware/frontend timer para cierre de sesión por inactividad tras 15 minutos (**US-0003 - Escenario 2**).