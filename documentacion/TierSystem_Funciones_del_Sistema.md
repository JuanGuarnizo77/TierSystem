# TierSystem — Funciones del Sistema por Actor

> Documento de referencia funcional y técnico, basado en el SRS (Documento de requerimientos de software) de TierSystem v1.0 y las Historias de Usuario (US-0001 a US-0049).
> 
> **Estado de avance actual:**
> - ✅ **Módulo de Administrador:** **100% Implementado** (Gestión de laboratoristas y agricultores, supervisión con exportación PDF/Excel, diagnóstico de hardware en tiempo real, catálogo de cultivos, rangos agronómicos de referencia, fallback/timeout de IA y métricas de laboratoristas).
> - ✅ **Autenticación y Perfiles:** Registro con activación inmediata, login multirrol, cierre de sesión, recuperación de contraseña por correo con token criptográfico y validación interactiva (US-0004), y perfil de usuario con edición de datos y clave para los 3 roles con acceso directo en la barra superior (US-0005).
> - ✅ **Soporte Offline y Estilos:** Tailwind CSS y FontAwesome integrados localmente en `static/` para funcionamiento autónomo sin CDN.
> - ✅ **Módulo de Mercado:** Precios SIPSA/DANE, histórico trimestral, tendencias de mercado y directorio de compradores regionales.
> - ✅ **Captura y Análisis:** Conexión con sensor ESP32/RS485, lectura de 7 parámetros de suelo, motor de análisis con fallback a base local y compartición de resultados con el agricultor.
> - ⏳ **Próximo foco de trabajo (Backlog):** Guía de 1 a 5 puntos de muestreo en campo (US-0026), cálculo de perfil promedio (US-0027), y comparador de dos análisis en historial (US-0011 / US-0033).

---

## 1. Contexto general del sistema

TierSystem es una plataforma web para análisis de suelo en campo, dirigida a agricultores del departamento del Huila. El flujo central es:

1. El **Agricultor** crea una solicitud de análisis (terreno + cultivo deseado).
2. El **Laboratorista** recibe la solicitud, la acepta, se traslada a campo, conecta el **sensor ESP32**, y realiza la captura de datos del suelo por puntos de muestreo.
3. El sistema valida los datos y calcula el **perfil del suelo**, enviándolo al **Servicio de IA** (o al motor de reglas local si no hay internet).
4. La IA (o el motor local) devuelve el **porcentaje de compatibilidad**, el semáforo de los 7 parámetros, recomendaciones agronómicas y cultivos alternativos.
5. El Laboratorista revisa el dictamen técnico y lo **comparte con el Agricultor**.
6. Existe también un módulo de **inteligencia de mercado** (SIPSA/DANE) para consulta de precios, cotizaciones históricas y compradores regionales, independiente del flujo de análisis.

El sistema funciona con capacidad de trabajo **offline** en campo (sin internet), sincronizando los registros al recuperar conectividad.

---

## 2. Actores del sistema

| Actor | Tipo | Rol principal | Estado de Implementación |
|---|---|---|---|
| **Agricultor** | Usuario | Solicita análisis, consulta resultados, historial y mercado | **92% Completado** ✅ |
| **Laboratorista** | Usuario operativo | Gestiona solicitudes, opera el sensor en campo, genera y comparte análisis | **88% Completado** ✅ |
| **Administrador** | Usuario de gestión | Administra cuentas, configuración, supervisión, reportes PDF/Excel y hardware | **100% Completado** ✅ |
| **Sensor (ESP32 + RS485)** | Actor externo de hardware | Captura y transmite los 7 parámetros físicos y químicos del suelo | **100% Integrado** ✅ |
| **Servicio de IA (API)** | Actor externo de software | Calcula compatibilidad, genera recomendaciones y alternativas (con fallback local) | **100% Integrado** ✅ |

---

## 3. Matriz de Estado de Historias de Usuario (US-0001 a US-0049)

| ID | Historia de Usuario | Actor | Estado | Módulo / Ubicación |
|---|---|---|---|---|
| **US-0001** | Registro de cuenta personal por cuenta propia | Agricultor | ✅ Implementado | `apps/usuarios/views.py` (`registro_agricultor`) |
| **US-0002** | Inicio de sesión con credenciales | Todos los roles | ✅ Implementado | `apps/usuarios/views.py` (`login_view`) |
| **US-0003** | Cierre de sesión seguro | Todos los roles | 🟡 Parcial | Escenario 1 (Manual) ✅ / Escenario 2 (Inactividad) ⏳ |
| **US-0004** | Recuperación de contraseña vía email con token seguro | Todos los roles | ✅ Implementado | `templates/usuarios/password_reset_*` y `apps/usuarios/urls.py` |
| **US-0005** | Consulta y edición de perfil personal y cambio de clave | Todos los roles | ✅ Implementado | `perfil_admin`, `perfil_laboratorista`, `perfil_agricultor` |
| **US-0006** | Consulta de terrenos registrados | Agricultor | ✅ Implementado | `apps/terrenos/views.py` (`lista_terrenos`) |
| **US-0007** | Registro de terrenos (nombre + área en m² o ha) | Agricultor | ✅ Implementado | `apps/terrenos/views.py` (`crear_terreno`) |
| **US-0008** | Edición y eliminación de terrenos (con confirmación) | Agricultor | ✅ Implementado | `apps/terrenos/views.py` (`editar_terreno`, `eliminar_terreno`) |
| **US-0009** | Creación de solicitud de análisis de suelo | Agricultor | ✅ Implementado | `apps/solicitudes/views.py` (`crear_solicitud`) |
| **US-0010** | Consulta de estado y cancelación de solicitud activa | Agricultor | ✅ Implementado | `apps/solicitudes/views.py` (cancelable solo en Pendiente) |
| **US-0011** | Consulta de historial de análisis y comparativa | Agricultor | 🟡 Parcial | Escenarios 1-3 (Historial) ✅ / Escenarios 4-5 (Comparador) ⏳ |
| **US-0012** | Exportación de historial de análisis a PDF / Excel | Agricultor | ⏳ Pendiente | Pendiente desarrollo en portal agricultor |
| **US-0013** | Consulta de precio actual de cultivos (SIPSA/DANE) | Agricultor | ✅ Implementado | `apps/mercado/views.py` (`mercado_precios`) |
| **US-0014** | Historial de variaciones de precios de últimos 3 meses | Agricultor | ✅ Implementado | `apps/mercado/views.py` |
| **US-0015** | Consulta de tendencias de mercado (al alza, estable, baja) | Agricultor | ✅ Implementado | `apps/mercado/views.py` |
| **US-0016** | Directorio de compradores activos en la región | Agricultor | ✅ Implementado | `apps/mercado/views.py` |
| **US-0017** | Selector dinámico de cultivo en módulo de mercado | Agricultor | ✅ Implementado | `apps/mercado/views.py` |
| **US-0018** | Registro de nuevas cuentas de Laboratoristas por Admin | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_crear_laboratorista`) |
| **US-0019** | Activación y desactivación de cuentas de Laboratoristas | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_toggle_laboratorista`) |
| **US-0020** | Eliminación permanente de cuentas de usuarios | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_eliminar_usuario`) |
| **US-0021** | Consulta de solicitudes de análisis pendientes | Laboratorista | ✅ Implementado | `apps/solicitudes/views.py` (`solicitudes_laboratorista`) |
| **US-0022** | Aceptación o rechazo de solicitudes de análisis | Laboratorista | ✅ Implementado | `apps/solicitudes/views.py` (`aceptar_solicitud`, `rechazar_solicitud`) |
| **US-0023** | Actualización de estados del ciclo de la solicitud | Laboratorista | ✅ Implementado | `apps/solicitudes/views.py` |
| **US-0024** | Conexión con sensor ESP32 y verificación de estado | Laboratorista | ✅ Implementado | `apps/sensores/views.py` |
| **US-0025** | Supervisión de captura de datos del suelo en tiempo real | Laboratorista | ✅ Implementado | `apps/sensores/views.py` (`api/lecturas/`) |
| **US-0026** | Visualización y registro de puntos de muestreo (1 a 5) | Laboratorista | ⏳ Pendiente | Pendiente flujo de avance por puntos en campo |
| **US-0027** | Cálculo del perfil promedio del suelo | Laboratorista | ⏳ Pendiente | Pendiente consolidación multilectura |
| **US-0028** | Consulta de parámetros ideales del cultivo | Laboratorista | ✅ Implementado | `apps/analisis/views.py` |
| **US-0029** | Consulta de resultados emitidos por motor de IA | Laboratorista | ✅ Implementado | `apps/ia_recomendaciones/views.py` y `apps/analisis/views.py` |
| **US-0030** | Visualización de resultado integral en pantalla unificada | Laboratorista | ✅ Implementado | `templates/analisis/detalle.html` |
| **US-0031** | Compartir resultados con Agricultor y finalizar solicitud | Laboratorista | ✅ Implementado | `apps/solicitudes/views.py` (`compartir_analisis`) |
| **US-0032** | Operación offline, motor local y sincronización | Laboratorista | ✅ Implementado | Motor de reglas local y etiquetado de dictamen |
| **US-0033** | Consulta de historial de análisis del Laboratorista | Laboratorista | 🟡 Parcial | Escenario 1 (Historial) ✅ / Escenario 2 (Comparación) ⏳ |
| **US-0034** | Consulta global de análisis registrados en el sistema | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_supervision`) |
| **US-0035** | Reportes con filtros avanzados y exportación PDF/Excel | Administrador | ✅ Implementado | `admin_exportar_pdf`, `admin_exportar_excel` |
| **US-0036** | Supervisión de hardware y componentes en tiempo real | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_hardware`) |
| **US-0037** | Gestión de base de datos de cultivos (CRUD) | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_cultivos`) |
| **US-0038** | Configuración de rangos agronómicos de referencia | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_rangos`) |
| **US-0039** | Configuración de timeout y fallback de IA | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_ia_config`) |
| **US-0040** | Auditoría y consulta de actividad de Laboratoristas | Administrador | ✅ Implementado | `apps/usuarios/views.py` (`admin_laboratoristas_actividad`) |
| **US-0041** | Notificación de estado operativo del sensor | Sensor (ESP32) | ✅ Implementado | Firmware C++ / Endpoint de monitoreo |
| **US-0042** | Captura de parámetros físicos ante comando | Sensor (ESP32) | ✅ Implementado | Firmware C++ |
| **US-0043** | Lectura Modbus RTU de sonda RS485 | Sensor (ESP32) | ✅ Implementado | `documentacion/conexion.md` |
| **US-0044** | Envío de lecturas vía WiFi / HTTP al servidor | Sensor (ESP32) | ✅ Implementado | `POST /api/lecturas/` |
| **US-0045** | Recepción de lecturas por servicio de IA | Servicio de IA | ✅ Implementado | `apps/ia_recomendaciones/service.py` |
| **US-0046** | Procesamiento y preparación de datos del suelo | Servicio de IA | ✅ Implementado | Validación y normalización de variables |
| **US-0047** | Cálculo de compatibilidad agronómica | Servicio de IA | ✅ Implementado | Evaluación contra requerimientos del cultivo |
| **US-0048** | Generación de mejoras y cultivos alternativos | Servicio de IA | ✅ Implementado | Acciones de enmienda y opciones con compatibilidad > 50% |
| **US-0049** | Emisión de dictamen consolidado al sistema | Servicio de IA | ✅ Implementado | Retorno de carga analítica completa |

---

## 4. Funciones por actor (resumen de estado)

### 4.1 Agricultor
- Registrarse por su cuenta con activación automática. **(✅ Implementado)**
- Iniciar sesión / cerrar sesión / recuperar contraseña vía email con token seguro. **(✅ Implementado)**
- Ver y editar su perfil personal y cambiar contraseña. **(✅ Implementado)**
- Registrar, consultar, editar y eliminar terrenos (nombre + área en m² o ha). **(✅ Implementado)**
- Crear una solicitud de análisis (terreno + cultivo + modalidad: llevar muestra o pedir visita). **(✅ Implementado)**
- Consultar el estado de su solicitud activa y cancelarla (solo si está en estado **Pendiente**). **(✅ Implementado)**
- Consultar el resultado de un análisis ya compartido por el Laboratorista. **(✅ Implementado)**
- Consultar su historial de análisis completados. **(✅ Implementado)**
- Comparar dos análisis entre sí en el historial. **(⏳ Pendiente)**
- Exportar su historial de análisis en PDF o Excel. **(⏳ Pendiente)**
- Consultar precio actual del cultivo, historial de precios (3 meses), tendencias y compradores activos en su región (módulo de mercado, SIPSA/DANE). **(✅ Implementado)**

### 4.2 Administrador
- Iniciar sesión / cerrar sesión / recuperar contraseña / editar perfil personal. **(✅ Implementado)**
- Registrar cuentas de Laboratoristas (quedan **inactivas** hasta que el Administrador las active). **(✅ Implementado)**
- Activar / desactivar / eliminar permanentemente cuentas de Laboratoristas y Agricultores. **(✅ Implementado)**
- Consultar todos los análisis del sistema, generar reportes filtrados (usuario, fecha, cultivo) y exportarlos en **PDF y Excel**. **(✅ Implementado)**
- Ver el estado del hardware (sensor y componentes) con indicadores visuales en tiempo real. **(✅ Implementado)**
- Gestionar la base de datos local de cultivos (agregar, editar, eliminar) y configurar los **rangos agronómicos de referencia** (usados también por el motor offline). **(✅ Implementado)**
- Configurar el comportamiento del sistema ante fallos del servicio de IA (fallback y timeout). **(✅ Implementado)**
- Consultar la actividad y métricas de los Laboratoristas. **(✅ Implementado)**

### 4.3 Sensor (ESP32 + sonda RS485) — actor externo de hardware
- Informar su estado operativo al sistema (activo/inactivo, batería, última lectura). **(✅ Implementado)**
- Capturar parámetros físicos del suelo cuando recibe la orden de captura. **(✅ Implementado)**
- Obtener cada lectura individual desde la sonda vía **Modbus RTU sobre RS485**. **(✅ Implementado)**
- Enviar las lecturas al sistema vía **WiFi o Bluetooth** una vez completada la captura. **(✅ Implementado)**

### 4.4 Servicio de Inteligencia Artificial (API) — actor externo de software
- Recibir el perfil promedio del suelo + cultivo objetivo (vía HTTP/REST). **(✅ Implementado)**
- Validar que los datos estén completos y en rangos posibles. **(✅ Implementado)**
- Calcular el porcentaje de compatibilidad. **(✅ Implementado)**
- Generar recomendaciones de mejora para parámetros deficientes/excesivos. **(✅ Implementado)**
- Sugerir cultivos alternativos cuando la compatibilidad es baja (<50%). **(✅ Implementado)**
- Devolver el resultado completo del análisis y reintentar el envío si el sistema no confirma recepción a tiempo. **(✅ Implementado)**

---

## 5. Laboratorista — funciones en detalle

El Laboratorista es el actor operativo: trabaja **en campo, desde un dispositivo móvil**, con conectividad limitada o nula.

### 5.1 Cuenta, sesión y perfil
- **Iniciar sesión** con credenciales.
- **Cerrar sesión** voluntariamente o por inactividad.
- **Recuperar contraseña** vía correo electrónico con token de un solo uso.
- **Ver y editar su perfil** personal con cambio seguro de contraseña (`templates/laboratorista/perfil.html`).

### 5.2 Gestión de solicitudes (RQF-3.3 y RQF-3.4)
- Consultar el **listado de solicitudes pendientes**, con datos del Agricultor, el predio y el cultivo objetivo.
- **Aceptar** o **rechazar** una solicitud (máximo **una solicitud activa a la vez**).
- **Actualizar el estado**: pasa a **En proceso** al iniciar el muestreo en campo y a **Finalizada** al entregar el resultado.

### 5.3 Conectividad y captura de datos del sensor (RQF-4)
- **Conexión con el ESP32:** Escaneo y verificación de enlace (indicador semafórico verde/rojo).
- **Captura de los 7 parámetros agronómicos:**
  - pH
  - Nitrógeno (N)
  - Fósforo (P)
  - Potasio (K)
  - Humedad (%)
  - Conductividad Eléctrica (CE)
  - Temperatura (°C)
- **Validación técnica de lecturas:** Validación contra rangos técnicos válidos antes de procesar el análisis.
- **Guía de puntos de muestreo (RQF-4.7):** *(⏳ Pendiente)* Guía visual de 1 a 5 puntos y conteo de avance.
- **Cálculo del perfil promedio (RQF-4.8):** *(⏳ Pendiente)* Consolidación de lecturas promedio antes de enviar a IA.

### 5.4 Análisis de compatibilidad de cultivos (RQF-5)
- Cálculo de compatibilidad: Alta (≥75%), Media (50–74%), Baja (<50%).
- Clasificación por parámetro: 🟢 Verde (óptimo), 🟡 Amarillo (deficiente), 🔴 Rojo (excesivo).
- Recomendaciones técnicas y cultivos alternativos sugeridos.
- Visualización en pantalla responsiva unificada y opción de compartir con el Agricultor.

### 5.5 Operación offline y sincronización (RQF-6)
- Caché local de cultivos y rangos de referencia agronómicos.
- Generación de dictamen con motor local cuando no hay internet (etiqueta "Análisis generado en modo local").
- Reenvío en segundo plano al recuperar conectividad.

---

## 6. Reglas de negocio del sistema

- **Cuentas y roles:** El Agricultor se registra por su cuenta y queda activo automáticamente; la cuenta del Laboratorista (creada por el Administrador) requiere activación manual previa.
- **Separación de roles:** Agricultor, Laboratorista y Administrador acceden de forma independiente y segura a sus propios paneles y módulos.
- **Solicitud activa:** Solo se permite **una solicitud activa por Agricultor** y **una solicitud activa por Laboratorista** a la vez.
- **Cancelación:** El Agricultor solo puede cancelar su solicitud mientras se encuentre en estado **Pendiente**.
- **Modo offline:** El sistema procesa análisis en campo sin conectividad y sincroniza al recuperar cobertura.
- **Gobernanza:** Solo el Administrador puede editar los rangos de referencia y la base de cultivos.

---

## 7. Notas técnicas de hardware y comunicación

- **Sonda:** Multiparamétrica NPK/pH/CE/Temperatura/Humedad, protocolo **Modbus RS485**.
- **ESP32 DevKitC V4:** Convertidor TTL–RS485 con pines UART2 (`RO`=5, `DI`=2, `DE`=15, `RE`=13).
- **Comunicación ESP32 ↔ Servidor:** WiFi / HTTP POST (`/api/lecturas/`) o Bluetooth.
- **Redes en campo:** Utilizar hotspot móvil en caso de redes con aislamiento AP/cliente.

---

## 8. Plan de Implementación de Funcionalidades Pendientes

Con el **módulo del Administrador 100% finalizado** y la infraestructura base consolidada, los siguientes pasos son:

1. **Guía de Puntos de Muestreo (US-0026):** Diseñar el flujo de registro punto por punto (1 a 5) en la interfaz del Laboratorista.
2. **Perfil Promedio de Suelo (US-0027):** Consolidar los promedios aritméticos de los 7 parámetros entre los puntos tomados antes de enviar a IA.
3. **Comparador de Análisis en Historial (US-0011 / US-0033):** Crear la vista de selección múltiple y tabla comparativa con indicadores de mejora y deterioro.
4. **Exportación de Historial para Agricultor (US-0012):** Endpoint y plantilla para exportación en PDF y Excel desde la cuenta del Agricultor.
5. **Timeout por Inactividad (US-0003 Escenario 2):** Configuración de cierre de sesión automático tras inactividad prolongada.
