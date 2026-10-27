# Informe Técnico de Errores y Soluciones - TierSystem

**Fecha:** 24 de octubre de 2026  
**Proyecto:** TierSystem (Django 5.x, Django REST Framework, SimpleJWT, SQLite, PythonAnywhere - Plan Gratuito, App Móvil Flutter "appi" con Shorebird)  
**Audiencia:** Estudiantes y aprendices ADSO (Tecnólogo en Análisis y Desarrollo de Software - SENA)  
**Objetivo:** Consignar de forma cronológica, técnica y didáctica las incidencias encontradas durante la jornada de despliegue, refactorización y pruebas, explicando su causa raíz y procedimiento de resolución.

---

## 1. Resumen Ejecutivo

Durante la jornada del 24 de octubre de 2026 se llevó a cabo el despliegue del nuevo catálogo centralizado de cultivos (`apps.cultivos.models.Cultivo`) en el entorno de producción (PythonAnywhere). Esto conllevó una migración de datos relacionales sin pérdida de registros históricos, la restauración del enrutador principal de la API (`api/urls.py`), ajustes en serializers y vistas de reportes para dar soporte a propiedades virtuales, y la puesta en marcha del motor de Inteligencia Artificial agronómica con Gemini. A su vez, se superaron restricciones críticas del entorno de alojamiento gratuito (cuota de almacenamiento en disco de ~512 MB, timeouts y versiones obsoletas de modelos de IA) y se implementó un algoritmo matemático con pesos reales para el cálculo de compatibilidad edáfica, garantizando la consistencia funcional tanto en el entorno web como en la aplicación móvil.

---

## 2. Línea de Tiempo del Día (24 de Octubre de 2026)

| Hora Aprox. | Hito / Incidencia | Acción Realizada |
| :--- | :--- | :--- |
| **10:20 - 10:36** | Limpieza inicial y preparación | Unificación de migraciones y limpieza de archivos `.pyc` huérfanos. |
| **15:36 - 16:23** | Ajustes de motor diagnóstico y reportes | Corrección de tipos `Decimal` a `float` y permisos de visualización para laboratorista. |
| **17:00 - 17:30** | Detección de fallo en API principal | Faltaban rutas globales en el servidor; `api/urls.py` estaba reemplazado por el de laboratorista. |
| **17:56** | Corrección E1 (`f4a0d882`) | Restauración de `api/urls.py` en git y servidor. |
| **18:00 - 18:50** | Migración compleja en producción (E2) | Backups (SQLite y JSON), scripts `pre_migracion.py` y `post_migracion.py`, ejecución de 7 migraciones sin pérdida. |
| **18:55** | Detección de entorno sin virtualenv (E3) | Error de SimpleJWT en consola por no activar `workon tiersys`. |
| **19:00** | Pruebas Swagger 401 (E4) | Corrección de encabezados ("Bearer Bearer") y cookies en `/api/v1/docs/`. |
| **19:12** | Corrección E5 y E6 (`2febb6fd`) | Adaptación de serializers a campos escribibles y filtros en `core/views.py` hacia `cultivo_deseado_ref__nombre`. |
| **19:15 - 19:25** | Falla de Gemini por disco y librería (E7) | Límite de disco (512 MB) en PythonAnywhere; limpieza de caché (`pip cache purge`) e instalación de `google-generativeai`. |
| **19:28** | Ajuste de modelo Gemini a 2.5 (`505089fd`) | El modelo `gemini-1.5-flash` no estaba activo. Cambio a 2.5 dio 404 (obsoleto para nuevos usuarios). |
| **19:33** | Corrección modelo Gemini definitivo (`9630b5f9`) | Configuración y prueba de `gemini-flash-lite-latest` en producción. |
| **19:40 - 19:45** | Corrección E9 y E10 (`bdee6732`) | Soporte para consulta de laboratorista en `api_consultar_ia_agricultor` y corrección de "N actual undefined". |
| **19:50 - 19:57** | Corrección E11 (`6275cf90`) | Reemplazo del 80% estático por compatibilidad matemática real (`puntuar_cultivo`) basada en rangos del catálogo. |

---

## 3. Detalle de Errores y Soluciones

---

### E1. Sobrescritura de `api/urls.py` en Producción

- **Síntoma:** Al consultar la documentación interactiva Swagger (`/api/v1/docs/`) o rutas como `/api/v1/auth/` y `/api/v1/agricultor/`, el servidor retornaba errores `404 Not Found`. Solo respondían los endpoints del módulo laboratorista.
- **Causa:** El archivo raíz `api/urls.py` en el servidor de producción había sido sobrescrito localmente con el contenido de `api/laboratorista/urls.py`, eliminando las inclusiones de `api.auth.urls`, `api.agricultor.urls`, `drf_spectacular` y el alias raíz.
- **Solución aplicada:** Se restauró la versión integral de `api/urls.py` en la máquina de desarrollo, se realizó commit y push. En el servidor se ejecutó una copia de resguardo (`cp api/urls.py ~/urls_servidor_copia.py`), seguido de `git restore api/urls.py` y `git pull` para avanzar en *fast-forward* al commit `f4a0d882`. Se validó con `python manage.py check`.
- **Archivos tocados:** `api/urls.py`.
- **Cómo se comprobó:** Ejecución exitosa de `python manage.py check` y verificación de disponibilidad de los endpoints en el navegador.
- **Estado:** **VERIFICADO**.
- **Cómo evitarlo:** No editar archivos directamente en el servidor de producción y evitar hacer pruebas manuales sin ramas o stashes de control.

---

### E2. Ejecución de 7 Migraciones Críticas Pendientes y Riesgo de Pérdida de Datos

- **Síntoma:** Tras el refactor arquitectónico que creó la aplicación `apps/cultivos` con el modelo unificado `Cultivo` (tabla `cultivos_cultivo` con 91 registros base generados por `seed_cultivos.py`), existían 7 migraciones pendientes en producción:
  1. `cultivos 0001_initial`
  2. `analisis 0004_...`
  3. `terrenos 0004_...`
  4. `solicitudes 0007_...`
  5. `mercado 0010_...`
  6. `ia_recomendaciones 0005_...`
  7. `sipsa 0002_...`
- **Causa:** Las migraciones de Django eliminaban tablas obsoletas (`CultivoIdeal` de 92 filas, `CultivoSipsa` de 10, `PrediccionPrecio` de 10, `PrecioMercado` de 23, `ProductoMercado` y campos M2M de comprador) y convertían columnas de texto libre (`cultivo_deseado`, `cultivo_principal`) en claves foráneas directas (`ForeignKey`) apuntando a la nueva tabla `cultivos_cultivo`. Los IDs numéricos antiguos no coincidían con los nuevos, por lo que una migración directa (`migrate`) vaciaría o desvincularía toda la información existente.
- **Solución aplicada:**
  1. **Respaldos de seguridad:** Copia física de la base SQLite (`db_respaldo_24oct.sqlite3` y `db_respaldo_antes_migrar.sqlite3`) y volcado JSON selectivo de 11 tablas (`respaldo_cultivos_24oct.json`).
  2. **Ensayo previo:** Se clonó la base a un directorio temporal (`~/TierSystem_prueba`) y se ensayó el procedimiento paso a paso.
  3. **Scripts de transición:**
     - `pre_migracion.py`: Se ejecutó en el servidor; creó tablas de respaldo internas `respaldo_*`, verificó conteos, desacopló claves foráneas poniéndolas en `NULL` y vació temporalmente `sipsa_preciosemanal` bajo transacción segura con capacidad de *rollback*.
     - `post_migracion.py`: Ejecutado tras las migraciones; re-enlazó las relaciones comparando nombres en minúsculas y sin acentos mediante alias controlados:
       - *Café (Variedad Castillo)* $\rightarrow$ *Café Castillo*
       - *Café (Variedad Borbón)* $\rightarrow$ *Café Borbón*
       - *Café (Variedad Caturra)* $\rightarrow$ *Café Caturra*
       - *Maíz (Híbrido Amarillo)* $\rightarrow$ *Maíz Híbrido*
       - *Frijol (Cargamanto)* $\rightarrow$ *Frijol Cargamanto*
       - *Mapeos por suposición:* *Arroz Blanco* $\rightarrow$ *Arroz Riego* y *Maíz Amarillo* $\rightarrow$ *Maíz Híbrido*.
       - Traspasó códigos DANE (10 cultivos) y reinsertó los 80 precios semanales de SIPSA vinculados a sus nuevos IDs.
  4. **Secuencia ejecutada:**
     ```bash
     python manage.py migrate cultivos
     python seed_cultivos.py
     python ~/pre_migracion.py
     python manage.py migrate
     python ~/post_migracion.py
     ```
- **Archivos tocados:** Base de datos `db.sqlite3` en el servidor, scripts temporales `pre_migracion.py` y `post_migracion.py`.
- **Cómo se comprobó:** `showmigrations` no reportó pendientes. Se validaron los registros en la base de datos: 91 cultivos activos, 10 con nombre DANE, 80 precios semanales, solicitud #6 enlazada al cultivo 77, solicitud #10 enlazada a café (ID 1), terreno #6 enlazado a ID 8 y recomendación #4 enlazada a ID 8. Las solicitudes 5 y 9, los terrenos 9 y 12 y las recomendaciones 5 y 6 quedaron en `None` porque originalmente no poseían cultivo asignado.
- **Estado:** **VERIFICADO**.
- **Cómo evitarlo:** Planificar migraciones en dos fases (fase 1: adición de campos nullable y migración de datos con script Django; fase 2: eliminación del campo viejo).

---

### E3. Ejecución de Comandos en Consola sin Virtualenv Activado

- **Síntoma:** Al ejecutar scripts o comandos de consola en PythonAnywhere aparecía:
  ```text
  ModuleNotFoundError: No module named 'rest_framework_simplejwt'
  ```
- **Causa:** La consola Bash de PythonAnywhere se abrió por defecto en el entorno global del sistema (Python 3.13) en lugar de cargar el entorno virtual del proyecto.
- **Solución aplicada:** Activar el entorno virtual mediante el wrapper de virtualenv:
  ```bash
  workon tiersys
  ```
  (El cual utiliza Python 3.10 con todos los paquetes del proyecto instalados).
- **Archivos tocados:** Ninguno (operacional en shell).
- **Cómo se comprobó:** Se ejecutó `python -c "import rest_framework_simplejwt; print('OK')"` imprimiendo `OK`.
- **Estado:** **VERIFICADO**.
- **Cómo evitarlo:** Configurar el archivo `~/.bashrc` del servidor para que inicialice automáticamente el virtualenv o verificar siempre el prompt `(tiersys)` antes de correr comandos.

---

### E4. Autenticación Fallida en Swagger UI (`401 token_not_valid`)

- **Síntoma:** Al probar endpoints autenticados (como el dashboard del laboratorista) en la interfaz Swagger (`/api/v1/docs/`), la API respondía `401 Unauthorized`:
  ```json
  {"detail": "Given token not valid for any token type", "code": "token_not_valid"}
  ```
- **Causa:** En la ventana modal de autorización de Swagger se pegó el token con el texto `"Bearer <token>"`. Dado que Swagger ya añade automáticamente la palabra `Bearer`, el encabezado HTTP resultante fue `Authorization: Bearer Bearer <token>`. Adicionalmente, el token se había pegado accidentalmente dentro del campo de autenticación por cookie de sesión (`sessionid`).
- **Solución aplicada:** Hacer clic en "Logout" en ambos esquemas de seguridad dentro de Swagger y volver a autenticar pegando exclusivamente la cadena alfanumérica del JWT en el esquema correspondiente.
- **Archivos tocados:** Ninguno (cliente Swagger).
- **Cómo se comprobó:** Endpoints `/api/v1/auth/login/` y `/api/v1/laboratorista/dashboard/` respondieron con código HTTP 200 y la información esperada.
- **Nota de seguridad:** Se identificó que el usuario de pruebas `lab` utilizaba una contraseña vulnerable visible en capturas de pantalla. Debe cambiarse inmediatamente en producción.
- **Estado:** **VERIFICADO**.
- **Cómo evitarlo:** Leer detenidamente la descripción del campo de autorización en OpenAPI/Swagger para verificar si ya preconfigura el esquema `Bearer`.

---

### E5. Fallo en Filtros de Reportes Web por Propiedades Virtuales

- **Síntoma:** Riesgo inminente de error `django.core.exceptions.FieldError: Cannot resolve keyword 'cultivo_deseado' into field` al exportar análisis a formato PDF o Excel cuando se filtraba por cultivo.
- **Causa:** En `apps/solicitudes/models.py` y `apps/terrenos/models.py`, el atributo `cultivo_deseado` y `cultivo_principal` pasaron a ser propiedades con `@property` (lectura y escritura a través de `cultivo_deseado_ref`), por lo que el ORM de Django no permite realizar filtros SQL directos con `.filter(solicitud__cultivo_deseado__icontains=...)`.
- **Solución aplicada:** Se modificaron las consultas en `core/views.py` para consultar el campo real en la tabla foránea:
  ```python
  analisis = analisis.filter(solicitud__cultivo_deseado_ref__nombre__icontains=cultivo_nombre)
  ```
- **Archivos tocados:** `core/views.py` (líneas 317, 358 y 407).
- **Cómo se comprobó:** El código fue corregido y versionado en el commit `2febb6fd`.
- **Estado:** **NO VERIFICADO** (se corrigió y desplegó a nivel de código preventivamente, pero no se realizó la prueba de descarga del archivo filtrado por cultivo en la interfaz web).
- **Cómo evitarlo:** Recordar que las `@property` de Python solo existen en memoria y no pueden ser traducidas a cláusulas `WHERE` de SQL por el QuerySet de Django.

---

### E6. Deserialización de Solo Lectura para Cultivos en la API de Agricultor

- **Síntoma:** Al crear o actualizar un terreno o una solicitud desde la app móvil Flutter, el valor de `cultivo_principal` o `cultivo_deseado` no se guardaba en la base de datos o era ignorado por el serializador.
- **Causa:** Como `cultivo_principal` y `cultivo_deseado` eran propiedades `@property` en el modelo y no columnas físicas, Django REST Framework los consideraba automáticamente como campos de solo lectura (`read_only=True`).
- **Solución aplicada:** En `api/agricultor/serializers.py` se definieron explícitamente como campos de texto (`serializers.CharField`), permitiendo su escritura, y se implementó la función `_validar_cultivo` para verificar que el cultivo ingresado (por nombre o por ID numérico) exista efectivamente en el catálogo `apps.cultivos.models.Cultivo`:
  ```python
  def _validar_cultivo(value):
      value = str(value or '').strip()
      if not value:
          return value
      if value.isdigit():
          existe = Cultivo.objects.filter(id=int(value)).exists()
      else:
          existe = Cultivo.objects.filter(nombre__icontains=value).exists()
      if not existe:
          raise serializers.ValidationError("El cultivo no existe en el catálogo.")
      return value
  ```
- **Archivos tocados:** `api/agricultor/serializers.py`.
- **Cómo se comprobó:** Código desplegado en el commit `2febb6fd`.
- **Estado:** **NO VERIFICADO** (se omitió la ejecución de una petición `POST` real desde la aplicación Flutter por decisión del flujo de trabajo).
- **Cómo evitarlo:** Definir siempre la representación de lectura y escritura (`to_internal_value` o campos explícitos) en DRF cuando se manejan propiedades calculadas en modelos.

---

### E7. Falla de Gemini en Producción: Librería Ausente, Disco Lleno y Paquete Corrupto

- **Síntoma:** La plataforma no generaba recomendaciones agronómicas con IA. Al acceder a `/api/ia/consultar-agricultor/` se devolvía un error HTTP 500 o se activaba el cálculo de respaldo local sin conexión a Gemini.
- **Causa:**
  1. En el entorno de PythonAnywhere no estaba instalada la librería `google-generativeai` ni existía el archivo `.env`.
  2. Al ejecutar `pip install google-generativeai`, el comando abortó con el error:
     ```text
     OSError: [Errno 122] Disk quota exceeded
     ```
     La cuota de disco del plan gratuito de PythonAnywhere es de ~512 MB y el almacenamiento estaba ocupado en ~480 MB (`.virtualenvs` 221 MB, `TierSystem` 164 MB, `.cache` 64 MB, `.local` 23 MB).
  3. La interrupción abrupta de `pip` dejó el paquete `google_api_python_client-2.201.0.dist-info` en estado corrupto (sin archivo `METADATA`), impidiendo futuras instalaciones con error `FileNotFoundError`.
- **Solución aplicada:**
  1. Limpieza total de la caché de pip para liberar 64 MB:
     ```bash
     pip cache purge
     ```
  2. Eliminación manual del paquete corrupto en el directorio de site-packages.
  3. Instalación ligera sin caché:
     ```bash
     pip install --no-cache-dir google-generativeai
     ```
     (Quedó instalada la versión 0.8.6, dejando el uso total de disco en ~488 MB).
  4. Creación del archivo `~/TierSystem/.env` con permisos restringidos (`chmod 600`) para resguardar la variable `GEMINI_API_KEY`.
- **Archivos tocados:** Archivo `.env` en el servidor, entorno virtual `tiersys`.
- **Cómo se comprobó:** Se verificó la importación del SDK desde una consola Python con la clave cargada.
- **Estado:** **VERIFICADO**.
- **Avisos pendientes:** `google-generativeai` emite una advertencia de descontinuación (`FutureWarning`); se deberá migrar a la nueva librería `google.genai`. Python 3.10 ya perdió soporte oficial por parte de `google.api_core`.
- **Cómo evitarlo:** Monitorear el espacio en disco con `du -sh ~` antes de instalar dependencias pesadas en entornos compartidos y utilizar siempre el flag `--no-cache-dir`.

---

### E8. Modelos de Gemini Incompatibles o Descontinuados

- **Síntoma:** Las peticiones a la API de Gemini fallaban con error HTTP 404:
  ```text
  NotFound: 404 models/gemini-2.5-flash is not found for API version v1beta, or is not available to new users.
  ```
- **Causa:**
  1. El código original usaba `gemini-1.5-flash`, el cual no estaba disponible para la clave API configurada.
  2. En el commit `505089fd` se intentó cambiar a `gemini-2.5-flash`, pero Google restringió este modelo para nuevos usuarios.
  3. Estar presente en el listado de modelos no asegura que la clave tenga cuota o permiso de invocación. Adicionalmente, `genai.GenerativeModel(nombre)` es una inicialización perezosa (lazy) y no valida el modelo contra la red; el error solo se manifiesta al invocar `generate_content()`.
- **Solución aplicada:**
  Se ejecutó un script de prueba interactivo probando candidatos reales. `gemini-flash-lite-latest` respondió exitosamente de forma inmediata, mientras que otros sufrieron timeout (504). Se configuró la lista de modelos prioritaria en:
  ```python
  ['gemini-flash-lite-latest', 'gemini-flash-latest']
  ```
  (Commit `9630b5f9`).
- **Archivos tocados:** `apps/ia_recomendaciones/views.py`.
- **Cómo se comprobó:** Invocación exitosa mediante script de consola recibiendo respuesta válida en formato JSON.
- **Estado:** **VERIFICADO**.
- **Cómo evitarlo:** Validar siempre la respuesta de los modelos mediante un test de invocación real (`generate_content`) y prever fallbacks a modelos lite o estables.

---

### E9. Error 500 en `/api/ia/consultar-agricultor/` al Consultar Laboratorista

- **Síntoma:** Cuando un laboratorista abría el modal de recomendación agronómica en `templates/laboratorista/historial.html` y consultaba un cultivo, la interfaz caía silenciosamente al modo offline sin mostrar el análisis con IA. En la consola de red el backend respondía con error HTTP 500.
- **Causa:** En `apps/ia_recomendaciones/views.py`, la vista `api_consultar_ia_agricultor` ejecutaba:
  ```python
  analisis = RegistroAnalisis.objects.get(
      solicitud_id=solicitud_id,
      solicitud__agricultor=request.user
  )
  ```
  Al estar autenticado como laboratorista, `solicitud__agricultor=request.user` no coincidía, lanzando una excepción `RegistroAnalisis.DoesNotExist` no capturada que derivaba en el error 500.
- **Solución aplicada:** Ampliar la cláusula mediante el objeto `Q` de Django para permitir al agricultor dueño O al laboratorista asignado a la solicitud:
  ```python
  analisis = RegistroAnalisis.objects.get(
      Q(solicitud__agricultor=request.user) | Q(solicitud__laboratorista_asignado=request.user),
      solicitud_id=solicitud_id,
  )
  ```
  Adicionalmente se capturó `RegistroAnalisis.DoesNotExist` para devolver un código HTTP 404 claro.
- **Archivos tocados:** `apps/ia_recomendaciones/views.py`.
- **Cómo se comprobó:** El endpoint respondió exitosamente para usuarios con rol laboratorista asignado.
- **Estado:** **VERIFICADO**.
- **Cómo evitarlo:** Tener en cuenta la matriz de control de acceso basada en roles (RBAC) cuando una vista es compartida entre múltiples tipos de actores.

---

### E10. Valor "undefined" en Parámetros NPK en Modo Offline

- **Síntoma:** Al fallar la conexión o usar el modo offline en la vista del laboratorista, el cuadro de diálogo mostraba:
  ```text
  N actual undefined mg/kg | P actual undefined mg/kg | K actual undefined mg/kg
  ```
- **Causa:** En el archivo JavaScript de `templates/laboratorista/historial.html`, el objeto de estado `analisisReporteActivo` guardaba los nutrientes bajo las propiedades abreviadas `n`, `p` y `k`, pero la función `calcularCultivoModoOffline` intentaba leer `a.nitrogeno`, `a.fosforo` y `a.potasio`.
- **Solución aplicada:** Se corrigieron las referencias en las líneas correspondientes de `templates/laboratorista/historial.html` para acceder a `a.n`, `a.p` y `a.k` (commit `bdee6732`).
- **Archivos tocados:** `templates/laboratorista/historial.html`.
- **Cómo se comprobó:** Se visualizó el cálculo offline en el navegador, mostrando los valores numéricos correctos (por ejemplo, `55 mg/kg`).
- **Estado:** **VERIFICADO**.
- **Cómo evitarlo:** Definir contratos de interfaz o esquemas TypeScript/JSDoc en el frontend para evitar discrepancias de nomenclatura en objetos JS.

---

### E11. Sesgo de Compatibilidad: Todos los Cultivos Retornaban 80%

- **Síntoma:** Sin importar si el suelo evaluado era óptimo, pobre o totalmente inadecuado para una planta, el reporte agronómico entregado por la IA siempre afirmaba que la compatibilidad era de exactamente un **80%**.
- **Causa:** El prompt enviado a Gemini incluía una plantilla JSON con valores de ejemplo estáticos (`"compatibilidad": 80`), y el modelo de lenguaje imitaba el valor del ejemplo en lugar de deducirlo rigurosamente.
- **Solución aplicada:**
  1. Se eliminó la responsabilidad de estimar el porcentaje a la IA generativa.
  2. Se construyó el algoritmo determinista `puntuar_cultivo()` en `apps/ia_recomendaciones/views.py`. Este método compara los parámetros químicos y físicos medidos (pH, N, P, K, Humedad, Temperatura, Conductividad) contra los límites mínimos y máximos registrados en `cultivos_cultivo`.
  3. **Ponderación técnica:**
     - pH: 25%
     - Nitrógeno (N): 15%
     - Fósforo (P): 15%
     - Potasio (K): 15%
     - Humedad: 10%
     - Temperatura: 10%
     - Conductividad: 10%
  4. Si el valor medido está dentro del rango ideal obtiene 100 puntos; si está por fuera, se descuenta de forma proporcional a la distancia.
  5. Se implementó la función normalizadora `_norm()` para ignorar tildes, mayúsculas y espacios al buscar en el catálogo.
  6. Si el cultivo no existe en la base de datos, `compatibilidad` se retorna como `null` y la interfaz despliega un distintivo gris ("Sin rangos en catálogo"). Gemini únicamente genera el texto descriptivo y las recomendaciones de fertilización (commit `6275cf90`).
- **Archivos tocados:** `apps/ia_recomendaciones/views.py`, `templates/laboratorista/historial.html` y `templates/agricultor/historial.html`.
- **Cómo se comprobó:** El usuario comprobó en pantalla que cultivos con requerimientos incompatibles ahora obtienen puntajes variables y reales acordes al suelo.
- **Limitación identificada:** La calidad del porcentaje depende directamente de la fidelidad agronómica de los datos precargados en `cultivos_cultivo`.
- **Estado:** **VERIFICADO**.
- **Cómo evitarlo:** No solicitar a modelos de lenguaje (LLM) cálculos matemáticos o tabulares críticos; utilizar código imperativo para las operaciones lógicas y delegar al LLM la redacción y síntesis en lenguaje natural.

---

### E12. Errores de Procedimiento en Consola

Durante las intervenciones se presentaron fallos de interacción en la consola de comandos de Linux:
- **Partición de comandos `sed`:** Al copiar y pegar cadenas con saltos de línea se generó el error `sed: -e expresión nº 1, carácter X: orden 's' sin terminar`. Solución: Usar bloques *heredoc* (`cat << 'EOF'`) o archivos temporales ejecutados con python.
- **Pegado del comando en lugar del output:** Se pegaron instrucciones en el prompt creyendo que era la salida de ejecución.
- **Falta de entorno virtual:** Olvido recurrente del comando `workon tiersys` al abrir terminales nuevas.
- **Confianza en la lista cruda de modelos de Google:** Asumir que la presencia de un modelo en la API implica habilitación y cuota de uso.
- **Instalación de librerías al límite del espacio:** Intentar instalar paquetes pesados sin verificar el espacio libre en disco en planes gratuitos.

---

## 4. Tabla de Archivos Modificados en la Jornada

| Archivo | Qué cambió | Commit(s) |
| :--- | :--- | :--- |
| `api/urls.py` | Restauración del enrutador central de la API (Swagger, Auth, Agricultor, Laboratorista). | `f4a0d882` |
| `api/agricultor/serializers.py` | Campos `cultivo_principal` y `cultivo_deseado` convertidos en CharField escribibles con validación `_validar_cultivo`. | `2febb6fd` |
| `core/views.py` | Corrección de filtros de consulta hacia el campo real `solicitud__cultivo_deseado_ref__nombre__icontains`. | `2febb6fd` |
| `apps/ia_recomendaciones/views.py` | 1. Actualización de modelos Gemini a `gemini-flash-lite-latest`.<br>2. Permiso a laboratoristas en consulta de análisis con `Q()`.<br>3. Algoritmo `puntuar_cultivo` y normalización `_norm`. | `505089fd`<br>`9630b5f9`<br>`bdee6732`<br>`6275cf90` |
| `templates/laboratorista/historial.html` | 1. Corrección de claves NPK (`a.n`, `a.p`, `a.k`) en modo offline.<br>2. Manejo de compatibilidad nula ("Sin rangos en catálogo"). | `bdee6732`<br>`6275cf90` |
| `templates/agricultor/historial.html` | Soporte para visualizar badge gris y mensaje cuando el cultivo carece de rangos en catálogo. | `6275cf90` |

---

## 5. Registro de Commits del Día (24 de Octubre de 2026)

Lista cronológica inversa de commits generados y desplegados durante la resolución de estas incidencias:

1. **`6275cf90`**: *Compatibilidad real con rangos del catalogo* (Algoritmo `puntuar_cultivo`, pesos NPK/pH y soporte en templates).
2. **`bdee6732`**: *Lab puede consultar cultivo; arreglar undefined NPK* (Filtro con `Q` en análisis y claves JS `a.n`, `a.p`, `a.k`).
3. **`9630b5f9`**: *Usar gemini-flash-lite-latest* (Selección del modelo operativo con menor latencia).
4. **`505089fd`**: *Actualizar modelos Gemini a 2.5-flash* (Intento de actualización de versión de modelo).
5. **`2febb6fd`**: *Fix filtro cultivo en reportes y guardar cultivo en serializers de la app* (Serializers escribibles y filtros en `core/views.py`).
6. **`f4a0d882`**: *fix: restaurar api/urls.py principal* (Restauración completa de rutas en el backend).

*(Commits previos del mismo día relacionados a funcionalidades de toma de muestras y reportes: `e650ba8f`, `36226f0f`, `5425d030`, `49a46187`, `18983062`, `45d351bd`, `af30c290`, `85ef9b62`, `46ce79ae`, `e9a53089`, `59b6cee1`, `1a76e485`, `33118ab6`, `b968342a`).*

---

## 6. Lecciones Aprendidas

1. **La IA generativa no debe hacer matemáticas:** Los LLM son modelos probabilísticos de lenguaje, no motores de cálculo determinista. Darles ejemplos con números fijos provoca sesgo de anclaje (el caso del 80%). Los cálculos numéricos deben realizarse siempre en el backend en Python y pasar los resultados a la IA como contexto informativo.
2. **Cuidado con los planes gratuitos en la nube:** Un límite de 512 MB de almacenamiento requiere extrema disciplina operativa. Es indispensable usar `--no-cache-dir` al instalar paquetes con `pip`, no dejar respaldos pesados en el home y monitorear la cuota con `du -sh ~`.
3. **Las propiedades virtuales (`@property`) no son columnas de base de datos:** No se pueden consultar directamente en sentencias `filter()` del ORM de Django ni son deserializadas automáticamente para escritura por DRF a menos que se definan explícitamente en el serializador.
4. **Estrategia para migraciones destructivas:** Cuando se altera un modelo central que alimenta llaves foráneas en cascada, nunca se debe correr `migrate` sin un plan de respaldo binario (copia SQLite) y textual (JSON), acompañado de scripts de pre y post migración con transacciones controladas.

---

## 7. Avisos y Observaciones que no son Errores

- **Advertencias de drf-spectacular:** Durante la generación del esquema OpenAPI en `/api/v1/docs/` se observan advertencias del tipo `unable to guess serializer` y advertencias de `operationId` duplicados. Estas alertas son informativas y no comprometen la operación del sistema ni la respuesta de los endpoints.
- **Cambios locales sin commitear en el servidor:** En el servidor de PythonAnywhere se identificó que existen modificaciones pendientes no versionadas en `apps/usuarios/models.py`, eliminaciones en `documentacion/` y archivos binarios `.pyc` que fueron versionados en commits antiguos. Se instruye **no realizar commits directamente desde el servidor**, sino mantener el flujo unidireccional: desarrollo local $\rightarrow$ Git $\rightarrow$ despliegue en producción con `git pull`.

---

## 8. Tareas Pendientes (Priorizadas)

1. **[Seguridad - Urgente]** Modificar la contraseña del usuario de pruebas `lab`, la cual es débil y fue expuesta en capturas de pantalla.
2. **[Backend / IA]** Actualizar la función `api_diagnosticar_ia` (la cual aún posee un ejemplo estático de compatibilidad de 85 en su prompt) para que adopte el cálculo de `puntuar_cultivo`.
3. **[Móvil]** Compilar y publicar la app Flutter mediante `shorebird release android` (versión 1.0.0+10), debido a que se incluyó el plugin nativo `geolocator` y los parches regulares de Shorebird solo admiten modificaciones en código Dart.
4. **[Repositorio]** Desversionar los archivos binarios de compilación `__pycache__/*.pyc` y consolidar la regla en `.gitignore`.
5. **[Infraestructura]** Monitorear rigurosamente el almacenamiento en PythonAnywhere (`du -sh ~`), dado que el uso se encuentra en ~488 MB (muy próximo a los 512 MB permitidos).
6. **[Mantenimiento de SDK]** Planificar la migración del paquete en desuso `google-generativeai` al nuevo estándar `google.genai`.
7. **[Funcionalidad]** Desarrollar la Fase 2 del módulo de toma de muestras (creación del endpoint "generar análisis" e integración del botón correspondiente en Flutter).
8. **[Pruebas]** Ejecutar la prueba funcional y de integración de E5 (reportes web filtrados) y E6 (creación de solicitud y terreno enviando cultivo desde la app móvil).

---

## 9. Diferencias Encontradas

Al cotejar el registro de Git y el código del repositorio frente a los antecedentes reportados, se encontraron los siguientes detalles técnicos exactos:
- **Commits adicionales del 24 de octubre:** Además de los 4 commits reportados inicialmente (`f4a0d882`, `2febb6fd`, `505089fd`, `9630b5f9`), se encontraron en el historial los commits `bdee6732` (*Lab puede consultar cultivo; arreglar undefined NPK*) y `6275cf90` (*Compatibilidad real con rangos del catalogo*), los cuales cerraron satisfactoriamente las incidencias E9, E10 y E11.
- **Líneas exactas de filtro en `core/views.py`:** En `core/views.py` la sustitución de `solicitud__cultivo_deseado__icontains` a `solicitud__cultivo_deseado_ref__nombre__icontains` en el commit `2febb6fd` se aplicó en las líneas 358 (función `exportar_pdf`) y 407 (función `exportar_excel`). En la línea 317 (`supervision_analisis`) dicho filtro ya había sido adaptado en el commit previo `33118ab6` durante la mañana.
- **Ruta del archivo de documentación:** Conforme a la solicitud, se creó un único archivo Markdown consolidado ubicado en `documentacion/INFORME_ERRORES_24OCT2026.md`.
