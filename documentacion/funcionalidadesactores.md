# TierSystem — Funciones del Sistema por Actor

> Documento de referencia funcional, basado en el SRS (Documento de requerimientos de software) de TierSystem v1.0.
> Objetivo de este documento: servir de guía de desarrollo, detallando **todas** las funciones del sistema separadas por actor (Agricultor, Administrador y Laboratorista), y cómo se espera que cada una se refleje en pantalla. Ya están construidos **Login, Registro y Pantalla de inicio**. El siguiente bloque a construir es el **módulo del Laboratorista**, con foco especial en la **conectividad y captura de datos del sensor ESP32** (sección 6.3), porque es la pieza que desbloquea todo el flujo de análisis — por eso esa sección tiene el mayor nivel de detalle.

---

## 1. Contexto general del sistema

TierSystem es una plataforma web para análisis de suelo en campo, dirigida a agricultores del Huila. El flujo central es:

1. El **Agricultor** crea una solicitud de análisis (terreno + cultivo deseado).
2. El **Laboratorista** recibe la solicitud, la acepta, se traslada a campo, conecta el **sensor ESP32**, hace la captura de datos del suelo por puntos de muestreo.
3. El sistema calcula el **perfil promedio del suelo** y lo envía al **Servicio de IA** (o usa el motor local si no hay internet).
4. La IA (o el motor local) devuelve el **porcentaje de compatibilidad**, el estado de cada parámetro, recomendaciones de mejora y cultivos alternativos.
5. El Laboratorista revisa el resultado y lo **comparte con el Agricultor**.
6. Existe también un módulo de **inteligencia de mercado** (SIPSA/DANE) para consulta de precios, independiente del flujo de análisis.

El sistema debe funcionar **offline** en campo (sin internet), sincronizando después.

---

## 2. Actores del sistema

| Actor | Tipo | Rol principal |
|---|---|---|
| **Agricultor** | Usuario | Solicita análisis, consulta resultados, historial y mercado |
| **Laboratorista** | Usuario operativo | Gestiona solicitudes, opera el sensor, genera y comparte análisis |
| **Administrador** | Usuario de gestión | Administra cuentas, configuración, supervisión y reportes |
| **Sensor (ESP32 + sonda RS485)** | Actor externo de hardware | Captura y transmite parámetros físicos del suelo |
| **Servicio de IA (API)** | Actor externo de software | Calcula compatibilidad, genera recomendaciones y alternativas |

---

## 3. Funciones por actor (resumen)

### 3.1 Agricultor

- Registrarse (cuenta se activa automáticamente, sin aprobación).
- Iniciar sesión / cerrar sesión / recuperar contraseña.
- Ver y editar su perfil.
- Registrar, consultar, editar y eliminar terrenos (nombre + área en m² o ha).
- Crear una solicitud de análisis (terreno + cultivo + modalidad: llevar muestra o pedir visita). **Solo puede tener una solicitud activa a la vez** (Pendiente, Aceptada o En proceso).
- Consultar el estado de su solicitud activa y cancelarla (solo si está en estado **Pendiente**).
- Consultar el resultado de un análisis ya compartido por el Laboratorista.
- Consultar, comparar y exportar su historial de análisis.
- Consultar precio actual del cultivo, historial de precios (3 meses), tendencias y compradores activos en su región (módulo de mercado, SIPSA/DANE).

### 3.2 Administrador

- Iniciar sesión / cerrar sesión / recuperar contraseña / editar perfil.
- Registrar cuentas de Laboratoristas (quedan **inactivas** hasta que el Administrador las active).
- Activar / desactivar / eliminar permanentemente cuentas de Laboratoristas y Agricultores.
- Consultar todos los análisis del sistema, generar reportes filtrados (usuario, fecha, cultivo) y exportarlos en **PDF y Excel**.
- Ver el estado del hardware (sensor y componentes) con indicadores visuales.
- Gestionar la base de datos local de cultivos (agregar, editar, eliminar) y configurar los **rangos agronómicos de referencia** (usados también por el motor offline).
- Configurar el comportamiento del sistema ante fallos del servicio de IA (fallback).
- Consultar la actividad de los Laboratoristas.

### 3.3 Sensor (ESP32 + sonda RS485) — actor externo de hardware

- Informar su estado operativo al sistema (activo/inactivo, batería, última lectura).
- Capturar parámetros físicos del suelo cuando recibe la orden de captura.
- Obtener cada lectura individual desde la sonda vía **Modbus RTU sobre RS485**.
- Enviar las lecturas al sistema vía **WiFi o Bluetooth** una vez completada la captura; reintenta si falla el envío.

### 3.4 Servicio de Inteligencia Artificial (API) — actor externo de software

- Recibir el perfil promedio del suelo + cultivo objetivo (vía HTTP/REST).
- Validar que los datos estén completos y en rangos posibles.
- Calcular el porcentaje de compatibilidad.
- Generar recomendaciones de mejora para parámetros deficientes/excesivos.
- Sugerir cultivos alternativos cuando la compatibilidad es baja (<50%).
- Devolver el resultado completo del análisis y reintentar el envío si el sistema no confirma recepción a tiempo.

---

## 4. Agricultor — funciones en detalle

El Agricultor es el usuario final del sistema: normalmente sin conocimientos técnicos, por lo que toda su interfaz debe ser simple e intuitiva. Es quien **origina** todo el flujo (crea la solicitud) y quien **recibe** el resultado al final. Se registra por su cuenta y su cuenta queda activa de inmediato, sin aprobación de nadie.

### 4.1 Cuenta y sesión (RQF-1.1, 1.5–1.8)

- **Registro** (RQF-1.1): formulario con nombre de usuario, teléfono y contraseña.
  - Se valida que todos los campos estén llenos y que el nombre de usuario no exista ya.
  - Al registrarse queda **activo automáticamente** y se le redirige directo a su panel principal (no hay paso de aprobación, a diferencia del Laboratorista).
  - En pantalla: si el usuario ya existe → mensaje "ese nombre ya está en uso"; si falta un campo → se marcan los campos obligatorios faltantes.
- **Inicio de sesión** (RQF-1.5): usuario/correo + contraseña → redirige a su panel. Si falla demasiadas veces, bloqueo temporal con aviso.
- **Cierre de sesión** (RQF-1.6): manual desde el menú de cuenta, o automático por inactividad (con aviso de "tu sesión expiró").
- **Recuperar contraseña** (RQF-1.7): pide correo/usuario → envía enlace de un solo uso al correo → el usuario define nueva contraseña → el enlace queda invalidado.
- **Ver/editar perfil** (RQF-1.8): pantalla con nombre de usuario y teléfono editables, y opción de cambiar contraseña (pide contraseña actual + nueva).

**En pantalla:** una sección de "Mi perfil" accesible desde un ícono/menú superior, con formulario simple de dos campos y un botón separado para "Cambiar contraseña".

### 4.2 Gestión de terrenos (RQF-2)

- **Registrar terreno** (RQF-2.1): formulario con **nombre** y **área** (en m² o hectáreas). Se valida que el área sea numérica y mayor a cero, y que el nombre no se repita.
- **Consultar terrenos** (RQF-2.2): listado de todos sus terrenos con nombre y área. Si no tiene ninguno, mensaje indicándolo (útil para mostrar un estado vacío con botón de "Registrar mi primer terreno").
- **Editar / eliminar terreno** (RQF-2.3):
  - Editar: formulario precargado con los datos actuales.
  - Eliminar: **modal de confirmación** que advierte que se eliminarán también todos los análisis asociados a ese terreno (acción permanente e irreversible). Si cancela, no pasa nada.

**En pantalla:** una vista tipo "Mis terrenos" con tarjetas o filas (nombre + área + botones editar/eliminar) y un botón flotante o de cabecera "+ Nuevo terreno".

### 4.3 Solicitudes de análisis (RQF-3.1 y 3.2)

- **Crear solicitud** (RQF-3.1):
  - Formulario: selección de **terreno** (de los ya registrados), **cultivo deseado**, y **modalidad de entrega** (llevar la muestra él mismo, o solicitar que el Laboratorista visite el terreno).
  - **Regla crítica:** solo puede tener **una solicitud activa** a la vez (Pendiente, Aceptada o En proceso). Si ya tiene una activa, el sistema se lo indica y no lo deja crear otra hasta que la actual termine (Finalizada) o se cancele.
  - Al confirmar, la solicitud queda en estado **Pendiente**.
- **Consultar y cancelar solicitud activa** (RQF-3.2):
  - Ve el estado actual: Pendiente / Aceptada / En proceso / Finalizada / Cancelada.
  - Solo puede **cancelar** mientras esté en **Pendiente** (con confirmación). Si ya fue Aceptada o está En proceso, el sistema le informa que ya no puede cancelarla.

**En pantalla:** una sección "Mi solicitud" que muestra, tipo línea de tiempo o "estado actual" destacado, con un botón "Cancelar" que solo aparece/activa cuando el estado lo permite. El formulario de creación solo se habilita si no hay una solicitud activa.

### 4.4 Resultados e historial (RQF-5.5 lectura, RQF-7)

- **Consultar el resultado** compartido por el Laboratorista: porcentaje de compatibilidad, estado de cada parámetro (verde/amarillo/rojo), recomendaciones de mejora y cultivos alternativos si aplica.
- **Historial de análisis** (RQF-7.1): lista ordenada de más reciente a más antiguo, con fecha, cultivo y % de compatibilidad. Los análisis generados offline muestran la etiqueta "Análisis generado en modo local".
- **Comparar dos análisis** (RQF-7.2): selecciona dos del historial → vista comparativa parámetro por parámetro, resaltando en verde las mejoras y en rojo los deterioros. Necesita al menos 2 análisis para poder comparar.
- **Exportar historial** (RQF-7.3): genera un archivo descargable con todo el historial. Si está vacío, se lo indica.

**En pantalla:** pantalla de "Resultados" con tarjetas de indicadores de color por parámetro y un botón "Ver detalle"; una sección "Historial" tipo lista/tabla con checkboxes para elegir dos y comparar, y un botón "Exportar".

### 4.5 Inteligencia de mercado (RQF-10)

- **Precio actual del cultivo** (RQF-10.1): selecciona/busca un cultivo → el sistema muestra el precio promedio regional (fuente SIPSA/DANE) y la fecha de última actualización. En offline, muestra la última consulta guardada con su fecha.
- **Historial de precios y tendencia** (RQF-10.2): gráfica de los últimos 3 meses, con flecha de tendencia (🟢 al alza / ⚪ estable / 🔴 a la baja), actualizada diariamente de forma automática.
- **Compradores activos en la región** (RQF-10.3): lista de compradores del cultivo consultado, con nombre, tipo (intermediario / plaza de mercado / cooperativa), municipio y contacto básico. Si no hay ninguno, sugiere contactar la cámara de comercio regional.
- **Cambiar de cultivo** (RQF-10.4): selector para cambiar el cultivo consultado; toda la sección de mercado se recarga con la info del nuevo cultivo.

**En pantalla:** un módulo independiente "Mercado" con un selector de cultivo arriba, precio destacado + gráfica de tendencia en el centro, y una lista de compradores abajo. Este módulo **no depende del flujo de análisis** — el Agricultor puede consultarlo en cualquier momento.

### 4.6 Interfaz esperada del Panel del Agricultor (checklist de UI, según el SRS)

- Indicador de estado de conexión (Online/Offline) siempre visible.
- Sección de gestión de terrenos con formulario de registro.
- Sección de solicitudes con estado de la solicitud activa y opción de cancelar.
- Pantalla de resultados con % de compatibilidad, indicadores de color por parámetro, recomendaciones y cultivos alternativos.
- Sección de historial de análisis, ordenada cronológicamente.
- Sección de inteligencia de mercado con precio actual, gráfica de tendencias y lista de compradores.

---

## 5. Administrador — funciones en detalle

El Administrador es el rol de gestión y supervisión: no opera en campo, usa el sistema desde **computador de escritorio o portátil**. Su nivel de experiencia esperado es alto (conoce el sistema y los parámetros técnicos del sensor). Su frecuencia de uso es media: configuración, supervisión periódica y gestión de usuarios/reportes.

### 5.1 Cuenta y sesión

Igual que los otros roles: iniciar/cerrar sesión, recuperar contraseña, ver/editar perfil (RQF-1.5 a 1.8). No tiene particularidades adicionales aquí.

### 5.2 Gestión de cuentas de usuarios (RQF-1.2, 1.3, 1.4)

- **Registrar Laboratoristas** (RQF-1.2):
  - Formulario: nombre, correo y contraseña.
  - Se valida que todos los campos estén completos y que el correo no esté ya registrado.
  - La cuenta se guarda en estado **inactivo**; el Laboratorista **no podrá iniciar sesión** hasta que el Administrador la active.
- **Activar / desactivar cuentas de Laboratoristas** (RQF-1.3):
  - Desde el listado, selecciona un Laboratorista → el sistema pide confirmación → al confirmar, cambia el estado.
  - Si se desactiva, ese Laboratorista no podrá iniciar sesión hasta ser reactivado. **No se borra su historial ni sus datos.**
- **Eliminación permanente de cuentas** (RQF-1.4): aplica tanto a Agricultores como a Laboratoristas.
  - Modal de confirmación que advierte que es una acción **permanente e irreversible** (se borra la cuenta y todos sus datos asociados).
  - Si cancela, no se hace ningún cambio.

**En pantalla:** dos listados separados — "Laboratoristas" y "Agricultores" — cada fila con nombre, estado (activo/inactivo) y botones de acción (Activar/Desactivar, Eliminar). El registro de un nuevo Laboratorista se hace desde un botón "+ Nuevo Laboratorista" que abre el formulario.

### 5.3 Supervisión y reportes (RQF-8)

- **Consulta de análisis de Agricultores** (RQF-8.1): puede ver los análisis de **un Agricultor específico** o **todos los análisis del sistema** sin filtrar, con fecha, cultivo y % de compatibilidad. Si no hay análisis, se le informa.
- **Actividad de Laboratoristas** (RQF-8.2): por cada Laboratorista, ve número de solicitudes atendidas, fechas de actividad y solicitudes en proceso. Si no tiene actividad, se indica.
- **Generación de reportes filtrados** (RQF-8.3): filtros por **usuario**, **rango de fechas** y **cultivo**. El sistema arma el reporte con los análisis que cumplan esos filtros; si ninguno cumple, se informa.
- **Exportación de reportes** (RQF-8.4): exporta el reporte generado en **PDF** o **Excel**. Si falla la generación, se informa y se ofrece reintentar.

**En pantalla:** un panel "Supervisión" con una barra de filtros (selector de usuario, rango de fechas, selector de cultivo), una tabla de resultados debajo, y dos botones de exportación ("Exportar PDF" / "Exportar Excel"). Una pestaña o sección aparte para "Actividad de Laboratoristas" con tarjetas por Laboratorista.

### 5.4 Administración y configuración del sistema (RQF-9)

- **Monitoreo del estado del hardware** (RQF-9.1): estado del sensor (activo/inactivo), nivel de batería, calidad de señal y última lectura registrada, **en tiempo real**. Alertas visuales si algún componente está anormal.
- **Configuración de rangos agronómicos** (RQF-9.2):
  - Formulario que muestra los rangos actuales por parámetro (pH, N, P, K, Humedad, CE, Temperatura).
  - El Administrador ingresa nuevos valores → el sistema valida que sean numéricos y coherentes → los guarda.
  - Estos rangos se aplican a los análisis futuros **y se incluyen en la próxima descarga local del Laboratorista** (alimentan también el motor offline).
- **Gestión de base de datos local de cultivos** (RQF-9.3): agregar cultivo (nombre + parámetros ideales), editar parámetros de uno existente, o eliminarlo. Al eliminar, no se afectan los análisis históricos que ya lo referenciaban. Esta base alimenta tanto el análisis online como el motor offline.
- **Configuración de fallback ante fallas de la API de IA** (RQF-9.4):
  - Define el **tiempo máximo de espera** (en segundos) para la respuesta de la API.
  - Elige el comportamiento ante fallo: (a) usar automáticamente la base de datos local, o (b) notificar al Laboratorista y cancelar el análisis.
  - La configuración se guarda y se aplica a todos los casos futuros.

**En pantalla:**
- "Estado del hardware": tarjetas o indicadores tipo semáforo por componente (sensor, batería, señal).
- "Rangos agronómicos": tabla editable con un campo mínimo/máximo por parámetro y botón "Guardar".
- "Cultivos": tabla tipo CRUD (agregar/editar/eliminar) con los parámetros ideales de cada uno.
- "Configuración de IA": formulario simple con un campo numérico (timeout) y un selector de dos opciones (usar local / cancelar y notificar).

### 5.5 Interfaz esperada del Panel del Administrador (checklist de UI, según el SRS)

- Listado de Laboratoristas con opciones de activar, desactivar o eliminar cuentas.
- Listado de Agricultores con opciones de activar, desactivar o eliminar cuentas.
- Sección de supervisión de análisis con filtros por usuario y fecha.
- Módulo de reportes con opciones de filtrado y botones de exportar en PDF y Excel.
- Sección de estado del hardware con indicadores visuales por componente.
- Formulario de configuración de rangos agronómicos.
- Gestión de base de datos local de cultivos.
- Panel de configuración del comportamiento ante fallos de la API.

---

## 6. Laboratorista — funciones en detalle (foco principal)

El Laboratorista es el actor operativo: trabaja **en campo, desde un dispositivo móvil**, con conectividad limitada o nula. Su cuenta la crea el Administrador y queda inactiva hasta ser activada. Nivel de experiencia esperado: intermedio (maneja el sensor y el proceso de muestreo).

### 6.1 Cuenta y sesión

- **Iniciar sesión** con usuario/correo + contraseña.
  - Si las credenciales son incorrectas → mensaje de error.
  - Si supera el límite de intentos fallidos → bloqueo temporal.
  - **Importante para offline:** el Laboratorista debe haber iniciado sesión al menos una vez con internet para poder iniciar sesión luego en modo offline, usando credenciales guardadas localmente.
- **Cerrar sesión** manualmente o automáticamente por inactividad (con aviso de expiración).
- **Recuperar contraseña** vía correo (enlace de un solo uso, con expiración configurable).
- **Ver y editar su perfil** personal.

### 6.2 Gestión de solicitudes (RQF-3.3 y RQF-3.4)

- Consultar el **listado de solicitudes pendientes**, con datos del Agricultor, el terreno y el cultivo deseado, antes de decidir.
- **Aceptar** o **rechazar** una solicitud.
  - Al aceptar → la solicitud pasa a estado **Aceptada**.
  - El sistema notifica al Agricultor del resultado (aceptada/rechazada).
  - **Regla clave:** el Laboratorista solo puede tener **una solicitud activa a la vez**. Las demás solicitudes pendientes pueden quedar sin fecha o con una fecha de atención asignada (funcionan como agenda de trabajo).
- **Actualizar el estado de la solicitud**:
  - Pasa a **En proceso** cuando el Laboratorista inicia el trabajo en campo.
  - Pasa a **Finalizada** automáticamente cuando comparte el resultado con el Agricultor.
  - Estados posibles: Pendiente → Aceptada → En proceso → Finalizada (o Cancelada, por el Agricultor).
  - El sistema notifica al Agricultor en cada cambio relevante.

### 6.3 Conectividad y captura de datos del sensor — **RQF-4 (el bloque que vas a construir ahora)**

Este es el módulo crítico. Aquí está el detalle completo, paso a paso, tal como lo especifica el SRS:

#### 6.3.1 Conexión con el módulo ESP32 (RQF-4.1)

- El Laboratorista entra a la sección de captura de su **solicitud activa**.
- El sistema **escanea automáticamente** la red WiFi o el entorno Bluetooth buscando el ESP32.
- Si lo detecta → establece conexión y muestra un **indicador verde**.
- Si no lo detecta → **indicador rojo** + mensaje pidiendo verificar que el sensor esté encendido y en rango.
- Si se pierde la conexión durante una captura → el sistema intenta reconectar automáticamente e informa el estado al Laboratorista en tiempo real.

#### 6.3.2 Verificación del estado del sensor (RQF-4.2)

Antes de capturar, el sistema debe mostrar:
- Estado: activo / inactivo.
- Nivel de batería.
- Última lectura registrada.
- Si algún componente está anormal → alerta indicando cuál.

#### 6.3.3 Captura de parámetros (RQF-4.3, RQF-4.5)

Los **7 parámetros** que mide la sonda por cada punto de muestreo:

| Parámetro | Sigla |
|---|---|
| pH | pH |
| Nitrógeno | N |
| Fósforo | P |
| Potasio | K |
| Humedad | — |
| Conductividad eléctrica | CE |
| Temperatura | — |

Flujo:
1. El Laboratorista, con el sensor conectado, presiona **"Capturar datos del suelo"**.
2. El sistema envía el **comando de lectura** al ESP32.
3. El ESP32 consulta la sonda vía **Modbus RTU / RS485** y obtiene los 7 valores.
4. El ESP32 **transmite** los 7 parámetros al sistema (vía WiFi o Bluetooth).
5. El sistema **muestra** los datos capturados y los **guarda con fecha y hora exactas**.
6. Si la sonda no responde → el sistema avisa al Laboratorista y ofrece **reintentar**.
7. Si la transmisión falla → el sensor reintenta el envío; si el error persiste, informa al Laboratorista.

#### 6.3.4 Validación de lecturas (RQF-4.6)

- El sistema compara cada lectura contra **rangos técnicos operativos válidos** (configurados por el Administrador).
- Si todas están dentro de rango → continúa hacia el análisis.
- Si alguna está fuera de rango → **alerta** al Laboratorista sugiriendo revisar posición y limpieza del sensor, y pide reintentar.
- **El sistema NO procesa el análisis** hasta tener una captura con datos válidos.

#### 6.3.5 Guía y registro de puntos de muestreo (RQF-4.7)

- El sistema calcula y muestra los **puntos de muestreo recomendados** según el área del terreno registrado.
- El Laboratorista marca cada punto como **"tomado"** conforme avanza en campo.
- El sistema muestra el avance (ej. "3 de 5 puntos completados").
- Si intenta finalizar con puntos insuficientes → advertencia, pero se le permite continuar de todas formas si decide hacerlo.

#### 6.3.6 Cálculo del perfil promedio del suelo (RQF-4.8)

- Al finalizar el muestreo, el Laboratorista presiona **"Finalizar muestreo"**.
- El sistema calcula el **promedio de cada uno de los 7 parámetros** entre todos los puntos capturados.
- Muestra el perfil promedio, con opción de ver el detalle por punto individual.
- Este perfil promedio es el que se envía luego al Servicio de IA (o al motor local).

> **Nota de diseño:** este submódulo (6.3) es el corazón de lo que necesitas hacer funcionar ahora. Depende de: (1) que el ESP32 pueda emitir una petición HTTP/WS con los 7 valores, (2) que el backend tenga un endpoint que reciba esos datos asociados a la solicitud activa y al punto de muestreo actual, y (3) que el frontend del Laboratorista refleje en tiempo real el estado de conexión, la captura y el avance de puntos.

### 6.4 Análisis de compatibilidad de cultivos (RQF-5, funciones del Laboratorista)

- **Consultar parámetros ideales del cultivo objetivo**: el sistema pide esto a la API de IA; si no hay internet o la API falla, usa la base de datos local como respaldo. El sistema le informa al Laboratorista cuál fuente está usando.
- **Ver el cálculo de compatibilidad**: porcentaje (Alta ≥75%, Media 50–74%, Baja <50%) y cada parámetro clasificado con color:
  - 🟢 Verde = óptimo
  - 🟡 Amarillo = deficiente
  - 🔴 Rojo = excesivo
- **Ver recomendaciones de mejora**: por cada parámetro fuera de óptimo, una acción concreta (qué aplicar / cómo corregir) y el impacto estimado en el porcentaje.
- **Ver cultivos alternativos** cuando la compatibilidad es baja, ordenados de mayor a menor compatibilidad, con posibilidad de ver el detalle de cada uno.
- **Visualizar el resultado completo** del análisis en una sola vista, adaptada a pantalla móvil, con opción de expandir cada sección. Si el resultado se generó offline, se muestra la etiqueta **"Análisis generado en modo local"**.
- **Compartir el resultado con el Agricultor**:
  - El Laboratorista revisa el resultado y presiona "Compartir".
  - El sistema notifica al Agricultor (push) y **cambia el estado de la solicitud a Finalizada** automáticamente.
  - Si no hay conexión, el sistema le avisa que la entrega quedará pendiente hasta que alguno de los dos dispositivos recupere internet.

### 6.5 Operación offline y sincronización (RQF-6, funciones del Laboratorista)

- Al iniciar sesión con internet, el sistema **descarga y guarda localmente**: cultivos, rangos agronómicos, y datos de la solicitud activa (esto se actualiza también cada vez que acepta una nueva solicitud).
- El sistema muestra **siempre visible** un indicador de estado de conexión (Online / Offline).
- Si no hay internet y ya se completó la captura del sensor, el Laboratorista puede **generar el análisis en modo offline** usando el motor local (rangos y cultivos guardados en el dispositivo, en MySQL local).
- El resultado offline se marca como **"Análisis generado en modo local"**.
- Al recuperar conexión, el sistema **reenvía los datos a la IA externa en segundo plano**; si el resultado de la IA difiere significativamente del local, notifica al Laboratorista y al Agricultor.
- **Sincronización automática**: al recuperar internet, el sistema sincroniza solo (sin acción manual) todos los datos pendientes; si falla, mantiene los datos en cola para reintentar y avisa al Laboratorista.

### 6.6 Historial (RQF-7, funciones compartidas con el Agricultor)

- Consultar el **historial de análisis realizados**, ordenado de más reciente a más antiguo (fecha, cultivo, % de compatibilidad). Los generados offline muestran su etiqueta.
- **Comparar dos análisis**: vista comparativa por parámetro, con verde para mejoras y rojo para deterioros. Requiere al menos 2 análisis.

---

## 7. Reglas de negocio del sistema (las tres actores)

**Cuentas y roles**
- El Agricultor se registra por su propia cuenta y queda activo automáticamente; la cuenta del Laboratorista (creada por el Administrador) requiere activación manual.
- **Separación estricta de roles**: el Agricultor no puede acceder a funciones del Laboratorista ni del Administrador, y viceversa — cada uno ve solo su panel correspondiente.
- La eliminación de cuentas de usuario y de terrenos es **permanente e irreversible**; ambas requieren confirmación previa.
- El enlace de recuperación de contraseña es de un solo uso y expira según configuración.
- Si un usuario falla el login más veces del límite configurado, el sistema bloquea el acceso temporalmente.

**Solicitudes**
- Un **Agricultor** solo puede tener **una solicitud activa** a la vez (Pendiente, Aceptada o En proceso); no puede crear otra hasta que la actual sea Finalizada o Cancelada.
- El Agricultor solo puede **cancelar** su solicitud mientras esté en estado **Pendiente**.
- Un **Laboratorista** solo puede atender **una solicitud activa a la vez**.

**Sensor y análisis**
- **No se puede iniciar el análisis** sin haber completado al menos el mínimo de puntos de muestreo recomendados, o sin una lectura válida del sensor.
- El sistema **no procesará lecturas fuera del rango técnico operativo** de la sonda; el Laboratorista debe repetir la captura.
- Eliminar un terreno elimina también todos sus análisis asociados. Eliminar un cultivo de la base local **no** afecta los análisis históricos que lo referenciaron.

**Modo offline**
- En modo offline, la **transferencia del resultado al Agricultor** requiere que al menos uno de los dos (Laboratorista o Agricultor) tenga conexión a internet.
- Los resultados offline **siempre** se marcan visiblemente como "Análisis generado en modo local".
- El módulo de mercado se actualiza diariamente; en offline muestra la última consulta guardada con su fecha.

**Configuración y reportes (exclusivo del Administrador)**
- **Solo el Administrador** puede modificar los rangos agronómicos de referencia y la base de datos local de cultivos (el Laboratorista y la IA solo los consumen).
- **Solo el Administrador** puede generar y exportar reportes.

---

## 8. Interfaz esperada del Panel del Laboratorista (según el SRS)

Esto es lo que el SRS espera ver en pantalla — útil como checklist de UI a construir después del login:

- Indicador de estado de conexión (**Online / Offline**) visible siempre.
- Listado de solicitudes con estado, datos del Agricultor y del terreno, y opción de asignar fecha de atención.
- Sección de **captura**: indicador de estado del sensor, guía de muestreo (puntos recomendados vs. tomados), botón de **capturar datos**.
- Pantalla de **resultado completo**, con etiqueta visible si el análisis fue generado en modo local.
- Opción de **compartir resultado** con el Agricultor.

---

## 9. Notas técnicas de hardware y comunicación (relevantes para hacer funcionar el sensor)

- **Sonda**: multiparamétrica NPK/pH/CE/Temperatura/Humedad, protocolo **Modbus RS485**.
- **ESP32 DevKitC V4**, conectado a la sonda mediante un **convertidor TTL–RS485**.
- Alimentación: sistema solar para el módulo en campo (para pruebas de escritorio no es necesario).
- Comunicación **sonda ↔ ESP32**: Modbus RTU sobre RS485.
- Comunicación **ESP32 ↔ plataforma web**: WiFi o Bluetooth.
- Comunicación **app web ↔ servidor**: HTTPS.
- Requisito no funcional relevante: el sistema debe procesar los datos del sensor y generar el análisis en **menos de 5 minutos** desde la captura.
- Recordatorio de tu propio historial de pruebas: las redes institucionales tipo "APRENDICES" suelen tener **aislamiento AP/cliente**, lo que bloquea la comunicación directa ESP32 → computador. Para probar el POST HTTP simulado, usa un **hotspot móvil personal** en vez de la red institucional.

---

## 10. Orden sugerido de implementación (a partir de lo que ya tienes)

Dado que ya tienes login, registro y pantalla de inicio, y quieres priorizar que el sensor funcione, un orden lógico sería:

1. **Solicitudes básicas**: que el Laboratorista pueda ver y aceptar una solicitud (aunque sea con datos de prueba/seed), para tener un contexto ("solicitud activa") al cual asociar la captura.
2. **Conexión con el ESP32** (4.3.1): pantalla con indicador verde/rojo, escaneo o al menos un botón "Conectar" que haga ping al endpoint del ESP32.
3. **Endpoint de recepción de datos del sensor** en tu backend (Flask u otro): recibe los 7 parámetros + timestamp, asociados a la solicitud activa y a un punto de muestreo.
4. **Botón de captura + guardado**: el Laboratorista dispara la captura, el sistema muestra los 7 valores recibidos y los guarda.
5. **Validación de rangos** (4.3.4): antes de aceptar la lectura como válida.
6. **Guía de puntos de muestreo** (4.3.5): marcar puntos como tomados y ver avance.
7. **Cálculo del perfil promedio** (4.3.6): una vez completados los puntos.
8. Recién ahí conectar con el módulo de análisis de compatibilidad (IA / motor local).

Este orden te permite tener el flujo sensor → captura → guardado funcionando de punta a punta antes de meterte con IA, offline o mercado.