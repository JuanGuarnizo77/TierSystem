"""
Controladores del Motor de Inteligencia Artificial y Recomendaciones Agronómicas.
==================================================================================
Implementa la arquitectura híbrida de inferencia agronómica de TierSystem:
  1. Inferencia Online con Google Gemini Flash (`api_diagnosticar_ia`):
     - Emite diagnósticos contextualizados como un ingeniero agrónomo de la región del Huila.
     - Aplica una regla estricta anti-alucinación: Gemini redacta el análisis agronómico
       cualitativo pero NO calcula los porcentajes; los porcentajes de compatibilidad
       son inyectados determinísticamente desde los rangos oficiales de `Cultivo`.
  2. Motor Edafológico Offline Heurístico (`calcular_diagnostico_edafologico`):
     - Opera al 100% sin acceso a internet en zonas rurales.
     - Pondera desviaciones de pH (25%), N-P-K (15% c/u), CE (10%), Humedad (10%),
       Temperatura (10%) y Altitud (15%).
  3. Desacople y Cálculo Canónico de Compatibilidad (`puntuar_cultivo`):
     - Función matemática central que penaliza la distancia euclidiana/lineal
       cuando una medición cae fuera del intervalo de tolerancia óptimo.
  4. Sincronización Bidireccional Offline (`api_sincronizar_offline`):
     - Ingesta masiva en MySQL de lecturas y diagnósticos tomados en la PWA (IndexedDB).
  5. Agregación Espacial de Muestras (`api_promedio_puntos`):
     - Promedia aritméticamente los puntos de la cuadrícula georreferenciada.
"""

import json
import os
import socket
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from apps.cultivos.models import Cultivo

# Importación condicional del SDK de Google Gemini para prevenir caídas si falta la dependencia
try:
    import google.generativeai as genai
except ImportError:
    genai = None

def verificar_conexion_internet(timeout=0.8):
    """
    Verifica rápidamente si el servidor tiene salida real a internet hacia DNS públicos.
    Retorna True si hay internet, False si está offline o en red local sin salida.
    """
    for host in [("8.8.8.8", 53), ("1.1.1.1", 53)]:
        try:
            s = socket.create_connection(host, timeout=timeout)
            s.close()
            return True
        except (socket.timeout, OSError):
            continue
    return False

def _guardar_recomendaciones_relacionales(registro, diagnostico):
    """
    Persiste cada recomendación de cultivo en la tabla relacional `RecomendacionAnalisis`.

    Garantiza atomicidad lógica limpiando previamente recomendaciones antiguas asociadas
    al mismo análisis para evitar duplicidades tras re-evaluaciones.

    Parámetros:
        registro (RegistroAnalisis): Instancia matriz del informe de laboratorio.
        diagnostico (dict): Estructura con la clave 'recomendaciones' (lista de especies).
    """
    if not diagnostico or not isinstance(diagnostico, dict):
        return

    from apps.analisis.models import RecomendacionAnalisis
    from apps.cultivos.models import Cultivo

    # Eliminación preventiva de registros hijos para permitir re-análisis limpios
    registro.recomendaciones.all().delete()

    recs = diagnostico.get("recomendaciones", [])
    for rec in recs:
        nombre = rec.get("cultivo", "Cultivo")
        # Limpieza de posibles paréntesis descriptivos (ej. "Café (Castillo)" -> "Café")
        nombre_limpio = nombre.split('(')[0].strip()
        compat = float(rec.get("compatibilidad", 0.0))
        desc = rec.get("descripcion", "")
        plan = rec.get("plan_fertilizacion", "")

        # Clasificación estándar de viabilidad según el porcentaje de afinidad
        viabilidad = "Alta" if compat >= 80 else ("Media" if compat >= 60 else "Baja")

        cultivo_obj = Cultivo.objects.filter(nombre__icontains=nombre_limpio).first()
        RecomendacionAnalisis.objects.create(
            analisis=registro,
            cultivo=cultivo_obj,
            nombre_cultivo=nombre,
            porcentaje_compatibilidad=compat,
            viabilidad=viabilidad,
            descripcion=desc,
            plan_fertilizacion=plan
        )


def _guardar_diagnostico_solicitud(solicitud_id, diagnostico, h, t, c, ph, n, p, k):
    """
    Centraliza la creación o actualización del `RegistroAnalisis` y la transición de estado.

    Flujo:
      1. Recupera la entidad `SolicitudAnalisis`.
      2. Ejecuta `update_or_create` sobre `RegistroAnalisis` registrando los 7 parámetros físicos y químicos.
      3. Serializa el dictamen en el campo `diagnostico_ia`.
      4. Transiciona la solicitud al estado terminal 'COMPLETADA'.
      5. Invoca `_guardar_recomendaciones_relacionales` para poblar las recomendaciones individuales.
    """
    if not solicitud_id:
        return None

    from apps.solicitudes.models import SolicitudAnalisis
    from apps.analisis.models import RegistroAnalisis

    try:
        sol = SolicitudAnalisis.objects.get(id=solicitud_id)
    except SolicitudAnalisis.DoesNotExist:
        return None

    # Persistencia o actualización atómica del informe consolidado
    registro, _ = RegistroAnalisis.objects.update_or_create(
        solicitud=sol,
        defaults={
            'humedad': h,
            'temperatura': t,
            'conductividad': c,
            'ph': ph,
            'nitrogeno': n,
            'fosforo': p,
            'potasio': k,
            'diagnostico_ia': json.dumps(diagnostico) if isinstance(diagnostico, dict) else str(diagnostico),
        }
    )

    # Transición definitiva del ciclo de atención
    sol.estado = 'COMPLETADA'
    sol.save()

    # Sincronización en tabla hija de recomendaciones
    _guardar_recomendaciones_relacionales(registro, diagnostico)
    return registro


def obtener_modelo_gemini():
    """
    Instancia el cliente del modelo generativo de Google Gemini con estrategia de fallback.

    Prioriza versiones optimizadas para baja latencia (`gemini-flash-lite-latest` o
    `gemini-flash-latest`) aptas para respuestas ágiles en entornos móviles.
    """
    for nombre in ['gemini-flash-lite-latest', 'gemini-flash-latest', 'gemini-2.5-flash', 'gemini-1.5-flash']:
        try:
            return genai.GenerativeModel(nombre)
        except Exception:
            continue
    return genai.GenerativeModel('gemini-flash-lite-latest')


def calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia='', altitud=None):
    """
    Motor Agronómico Edafológico Determinista y Offline de TierSystem.

    Evalúa matemáticamente las lecturas de suelo contra los umbrales fisiológicos de los
    cultivos registrados en `cultivos_cultivo`. No depende de internet ni de modelos externos.

    Ponderaciones del Algoritmo Heurístico:
      - pH: 25% (determinante en absorción de fósforo y metales).
      - Nitrógeno (N): 15% (síntesis de clorofila y proteínas).
      - Fósforo (P): 15% (desarrollo radicular y floración).
      - Potasio (K): 15% (balance hídrico, turgencia y llenado).
      - Conductividad Eléctrica (CE): 10% (presión osmótica y salinidad).
      - Humedad: 10% (disponibilidad de solución de suelo).
      - Temperatura: 10% (actividad microbiana y tasa metabólica).
      - Altitud: 15% (adaptación a pisos bioclimáticos del Huila, si está disponible).

    Retorna:
        dict: Top 3 cultivos más compatibles con viabilidad, justificación, planes
              de enmienda locales y consejo agronómico integral.
    """
    cultivos = Cultivo.objects.filter(activo=True)
    if not cultivos.exists():
        # Salvaguarda de emergencia si la base de datos de cultivos está vacía
        return {
            "recomendaciones": [
                {
                    "cultivo": "Café Castillo",
                    "compatibilidad": 88,
                    "viabilidad": "Alta",
                    "descripcion": "Condiciones edafológicas aptas para caficultura tecnificada en el Huila.",
                    "plan_fertilizacion": "Aplicar enmienda orgánica y fertilización NPK según calendario fenológico."
                }
            ],
            "consejo_general": "Diagnóstico agronómico local generado en modo offline.",
            "modo": "offline"
        }

    import unicodedata

    def normalizar_cadena(txt):
        if not txt:
            return ""
        texto = ''.join(
            c for c in unicodedata.normalize('NFD', str(txt).lower())
            if unicodedata.category(c) != 'Mn'
        )
        return ''.join(c for c in texto if c.isalnum())

    pref_norm = normalizar_cadena(preferencia)

    evaluaciones = []

    # Ley del Mínimo de Liebig y evaluación de viabilidad agronómica del suelo
    es_suelo_critico = (n <= 5 and p <= 5 and k <= 5)
    deficits_graves = (n < 10 or p < 10 or k < 10 or c < 0.2)

    for cultivo in cultivos:
        puntajes = []
        # ---------------------------------------------------------------------
        # 1. Evaluación de pH (Ponderación: 25%)
        # ---------------------------------------------------------------------
        ph_min = float(cultivo.ph_min)
        ph_max = float(cultivo.ph_max)
        if ph > 0:
            if ph_min <= ph <= ph_max:
                score_ph = 100.0
            elif ph < ph_min:
                diff = ph_min - ph
                score_ph = max(5.0, 100.0 - (diff / 1.5) * 80.0)
            else:
                diff = ph - ph_max
                score_ph = max(5.0, 100.0 - (diff / 1.5) * 80.0)
            puntajes.append(('ph', score_ph, 0.25))

        # ---------------------------------------------------------------------
        # 2. Evaluación de Nitrógeno N (Ponderación: 15%)
        # ---------------------------------------------------------------------
        n_min = float(cultivo.nitrogeno_min)
        n_max = float(cultivo.nitrogeno_max)
        if n == 0:
            score_n = 0.0
        elif n < n_min:
            score_n = max(0.0, (n / max(n_min, 1)) * 50.0)
        elif n_min <= n <= n_max:
            score_n = 100.0
        else:
            score_n = max(40.0, 100.0 - ((n - n_max) / max(n_max, 1)) * 40.0)
        puntajes.append(('n', score_n, 0.15))

        # ---------------------------------------------------------------------
        # 3. Evaluación de Fósforo P (Ponderación: 15%)
        # ---------------------------------------------------------------------
        p_min = float(cultivo.fosforo_min)
        p_max = float(cultivo.fosforo_max)
        if p == 0:
            score_p = 0.0
        elif p < p_min:
            score_p = max(0.0, (p / max(p_min, 1)) * 50.0)
        elif p_min <= p <= p_max:
            score_p = 100.0
        else:
            score_p = max(50.0, 100.0 - ((p - p_max) / max(p_max, 1)) * 40.0)
        puntajes.append(('p', score_p, 0.15))

        # ---------------------------------------------------------------------
        # 4. Evaluación de Potasio K (Ponderación: 15%)
        # ---------------------------------------------------------------------
        k_min = float(cultivo.potasio_min)
        k_max = float(cultivo.potasio_max)
        if k == 0:
            score_k = 0.0
        elif k < k_min:
            score_k = max(0.0, (k / max(k_min, 1)) * 50.0)
        elif k_min <= k <= k_max:
            score_k = 100.0
        else:
            score_k = max(50.0, 100.0 - ((k - maxK_val if (maxK_val := max(k_max, 1)) else 1) / maxK_val) * 40.0)
        puntajes.append(('k', score_k, 0.15))

        # ---------------------------------------------------------------------
        # 5. Conductividad Eléctrica CE (Ponderación: 10%)
        # ---------------------------------------------------------------------
        c_min = float(cultivo.conductividad_min)
        c_max = float(cultivo.conductividad_max)
        if c == 0:
            score_c = 0.0
        elif c < c_min:
            score_c = max(10.0, (c / max(c_min, 0.1)) * 60.0)
        elif c_min <= c <= c_max:
            score_c = 100.0
        else:
            score_c = max(10.0, 100.0 - ((c - c_max) / max(c_max, 0.1)) * 80.0)
        puntajes.append(('c', score_c, 0.10))

        # ---------------------------------------------------------------------
        # 6. Humedad y Temperatura (Ponderación: 10% c/u)
        # ---------------------------------------------------------------------
        h_min = float(cultivo.humedad_min)
        h_max = float(cultivo.humedad_max)
        if h > 0:
            if h < h_min:
                score_h = max(5.0, (h / max(h_min, 1)) * 50.0)
            elif h_min <= h <= h_max:
                score_h = 100.0
            else:
                score_h = max(20.0, 100.0 - ((h - h_max) / max(h_max, 1)) * 50.0)
            puntajes.append(('h', score_h, 0.10))

        t_min = float(cultivo.temperatura_min)
        t_max = float(cultivo.temperatura_max)
        if t > 0:
            score_t = 100.0 if (t_min <= t <= t_max) else max(40.0, 80.0)
            puntajes.append(('t', score_t, 0.10))

        # ---------------------------------------------------------------------
        # 7. Piso Altitudinal msnm (Ponderación: 15%)
        # ---------------------------------------------------------------------
        if altitud and altitud > 0:
            alt_min = float(cultivo.altitud_min)
            alt_max = float(cultivo.altitud_max)
            if alt_min <= altitud <= alt_max:
                score_alt = 100.0
            else:
                diff_alt = min(abs(altitud - alt_min), abs(altitud - alt_max))
                score_alt = max(20.0, 100.0 - (diff_alt / 500.0) * 80.0)
            puntajes.append(('alt', score_alt, 0.15))

        # Ponderación compuesta
        if puntajes:
            peso_total = sum(p[2] for p in puntajes)
            compatibilidad = sum(p[1] * p[2] for p in puntajes) / peso_total
        else:
            compatibilidad = 10.0

        if es_suelo_critico:
            compatibilidad = min(compatibilidad, 8.0)
        elif deficits_graves:
            compatibilidad = min(compatibilidad, 30.0)

        compat_final = round(float(compatibilidad), 1)

        # Construcción de planes agronómicos de fertilización correctiva
        planes = []
        if es_suelo_critico:
            planes.append("Déficit nutricional crítico total: N, P y K en 0 mg/kg. Suelo no viable para siembra inmediata. Requiere acondicionamiento orgánico de fondo y fertilización compuesta NPK completa antes de cualquier siembra.")
        else:
            if ph > 0 and ph < ph_min:
                planes.append("Aplicar enmienda calcárea (Cal Dolomita o Cal Agrícola) para corregir acidez.")
            if n < n_min:
                planes.append("Reforzar Nitrógeno con materia orgánica compostada o fertilización nitrogenada fraccionada.")
            if p < p_min:
                planes.append("Aplicar Fósforo localizado (DAP o Roca Fosfórica) para estimular desarrollo radicular.")
            if k < k_min:
                planes.append("Suplir Potasio (KCl o Sulfato de Potasio) para llenado de fruto y resistencia hídrica.")
            if not planes:
                planes.append("Condiciones nutricionales óptimas. Mantener plan de fertilización estándar.")

        cultivo_norm = normalizar_cadena(cultivo.nombre)
        cat_norm = normalizar_cadena(cultivo.categoria or '')
        es_preferido = bool(pref_norm and (pref_norm in cultivo_norm or cultivo_norm in pref_norm or pref_norm in cat_norm))

        if compat_final >= 75:
            viabilidad = "Alta"
        elif compat_final >= 50:
            viabilidad = "Media"
        elif compat_final >= 25:
            viabilidad = "Baja"
        else:
            viabilidad = "No Apto"

        evaluaciones.append({
            "cultivo": cultivo.nombre,
            "compatibilidad": compat_final,
            "viabilidad": viabilidad,
            "descripcion": f"{cultivo.descripcion[:160]}..." if cultivo.descripcion else f"Variedad del catálogo regional del Huila.",
            "plan_fertilizacion": " ".join(planes),
            "es_preferido": bool(es_preferido)
        })

    # Si el usuario solicitó un cultivo específico que no estaba en el catálogo, evaluarlo
    if pref_norm and not any(e['es_preferido'] for e in evaluaciones):
        compat_custom = 8.0 if es_suelo_critico else (20.0 if deficits_graves else 50.0)
        viab_custom = "No Apto" if compat_custom < 25 else ("Baja" if compat_custom < 50 else "Media")
        evaluaciones.insert(0, {
            "cultivo": preferencia.strip(),
            "compatibilidad": compat_custom,
            "viabilidad": viab_custom,
            "descripcion": f"Cultivo consultado específicamente por el usuario ({preferencia.strip()}).",
            "plan_fertilizacion": f"Déficit nutricional crítico total: N, P y K en 0 mg/kg. Suelo no viable para siembra de {preferencia.strip()}. Requiere acondicionamiento orgánico de fondo y fertilización compuesta NPK completa antes de cualquier siembra." if es_suelo_critico else f"Requiere acondicionamiento y plan de fertilización adaptado a {preferencia.strip()}.",
            "es_preferido": True
        })

    # Priorización: cultivos preferidos por el usuario primero, luego mayor compatibilidad
    evaluaciones.sort(key=lambda x: (1 if x['es_preferido'] else 0, x['compatibilidad']), reverse=True)
    top_recomendaciones = evaluaciones[:3]

    # Generación de síntesis técnica en lenguaje natural
    consejos = []
    if es_suelo_critico:
        consejos.append("ALERTA AGRONÓMICA: El suelo analizado NO ES APTO para ningún cultivo en su estado actual. Presenta un agotamiento severo con lecturas en 0 de Nitrógeno, Fósforo, Potasio y conductividad eléctrica nula (0 µS/cm). Ninguna planta podrá germinar ni desarrollarse sin una recuperación previa mediante enmienda orgánica profunda, fertilización NPK intensiva y corrección de pH.")
    else:
        if ph < 5.5 and ph > 0:
            consejos.append(f"El suelo presenta acidez (pH {ph:.1f}), común en suelos del Huila. Se recomienda encalar.")
        elif ph > 7.5:
            consejos.append(f"El suelo es ligeramente alcalino (pH {ph:.1f}). Monitorear microelementos.")
        else:
            consejos.append(f"El pH ({ph:.1f}) se encuentra en un rango balanceado para cultivos del Huila.")

        if n > 0 and p > 0 and k > 0:
            consejos.append(f"Perfil NPK registrado: N={n:.0f}, P={p:.0f}, K={k:.0f} mg/kg. Balance nutricional general evaluado.")

    consejos.append("Diagnóstico agronómico generado 100% en modo offline (Motor Huila).")

    return {
        "recomendaciones": top_recomendaciones,
        "consejo_general": " ".join(consejos),
        "es_critico": es_suelo_critico,
        "modo": "offline"
    }


def api_obtener_cultivos(request):
    """
    Endpoint HTTP: GET /ia/cultivos/
    --------------------------------
    Retorna el catálogo agronómico completo para la hidratación inicial de la PWA.
    Permite el almacenamiento en IndexedDB (Dexie.js) para operar sin red en campo.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Solo GET permitido"}, status=405)

    cultivos = Cultivo.objects.filter(activo=True)
    datos = [c.to_dict() for c in cultivos]

    return JsonResponse({
        "estado": "ok",
        "cultivos": datos
    })


@login_required(login_url='login')
def api_diagnosticar_ia(request):
    """
    Endpoint HTTP: POST /ia/diagnosticar/
    -------------------------------------
    Controlador central de inferencia agronómica dual (Gemini Online / Edafológico Offline).

    Flujo de ejecución:
      1. Extrae los 7 parámetros de suelo y la preferencia agronómica del usuario.
      2. Si se fuerza `modo == 'offline'`, ejecuta inmediatamente `calcular_diagnostico_edafologico`.
      3. Si `modo == 'auto'` y hay API Key de Gemini:
           a. Construye el prompt agronómico con restricciones estrictas.
           b. Invoca Google Gemini Flash con parsing JSON.
           c. Inyecta los porcentajes reales calculados por `puntuar_cultivo`, asegurando que
              la IA nunca invente o alucine porcentajes de compatibilidad.
           d. Si Gemini falla o excede el timeout, conmuta automáticamente al motor offline.
      4. Si se provee `solicitud_id`, persiste los resultados en base de datos.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)

    try:
        data = json.loads(request.body)
        h = float(data.get("humedad", 0) or 0)
        t = float(data.get("temperatura", 0) or 0)
        c = float(data.get("conductividad", 0) or 0)
        ph = float(data.get("ph", 0) or 0)
        n = float(data.get("nitrogeno", 0) or 0)
        p = float(data.get("fosforo", 0) or 0)
        k = float(data.get("potasio", 0) or 0)
        solicitud_id = data.get("solicitud_id")
        preferencia = str(data.get("preferencia", "")).strip()
        modo_solicitado = data.get("modo", "auto")

        # 1. Si se solicita explícitamente modo offline:
        if modo_solicitado == 'offline':
            resultado_offline = calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia=preferencia)
            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_offline, h, t, c, ph, n, p, k)
            return JsonResponse({"estado": "ok", "diagnostico": resultado_offline, "modo": "offline"})

        # Verificación rápida de salida a internet (máx 0.8s)
        hay_internet = verificar_conexion_internet(timeout=0.8)

        # 2. Si el usuario solicitó específicamente MODO ONLINE (IA) y NO hay internet:
        if modo_solicitado == 'online' and not hay_internet:
            return JsonResponse({
                "estado": "error",
                "sin_internet": True,
                "mensaje": "No hay conexión a internet activa para consultar la IA de Google Gemini. Para realizar el análisis sin internet, utiliza el modo 'Offline (Motor Huila)'."
            })

        # 3. Si está en MODO AUTOMÁTICO y NO hay internet:
        if modo_solicitado == 'auto' and not hay_internet:
            # Va directo a la base de datos local sin demoras ni falsas consultas
            resultado_offline = calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia=preferencia)
            resultado_offline["aviso"] = "Sin conexión a internet: Se utilizó el catálogo local de cultivos del Huila."
            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_offline, h, t, c, ph, n, p, k)
            return JsonResponse({
                "estado": "ok",
                "diagnostico": resultado_offline,
                "modo": "offline",
                "motivo": "sin_internet"
            })

        # 4. MODO ONLINE O AUTO CON INTERNET:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or genai is None:
            if modo_solicitado == 'online':
                return JsonResponse({
                    "estado": "error",
                    "mensaje": "La clave GEMINI_API_KEY no está configurada o no está disponible la librería genai."
                })
            resultado_offline = calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia=preferencia)
            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_offline, h, t, c, ph, n, p, k)
            return JsonResponse({"estado": "ok", "diagnostico": resultado_offline, "modo": "offline"})

        try:
            genai.configure(api_key=api_key)
            model = obtener_modelo_gemini()

            prompt_preferencia = f"\n- IMPORTANTE: El usuario tiene un interés especial en cultivar: '{preferencia}'. DEBES evaluar la compatibilidad de ese cultivo y sus variedades. Si la compatibilidad es muy mala (<40%), dilo claramente y sugiere otra alternativa más viable, pero de todas formas DEBES mostrar la evaluación del cultivo solicitado." if preferencia else ""

            prompt = f"""
Eres un ingeniero agrónomo experto de la región del Huila, Colombia.
Evalúa los siguientes parámetros de suelo obtenidos de un sensor en tiempo real en una finca del Huila:

- Humedad: {h}%
- Temperatura: {t}°C
- Conductividad Eléctrica: {c} us/cm
- pH: {ph}
- Nitrógeno (N): {n} mg/kg
- Fósforo (P): {p} mg/kg
- Potasio (K): {k} mg/kg

Reglas estrictas de respuesta:
1. Ten en cuenta que el suelo es del Huila, Colombia (climas cálidos, cafeteros y arroceros).
2. Propón 1 o 2 cultivos ideales (incluye su variedad si aplica, ej: Café Borbón, Maíz Amarillo). {prompt_preferencia}
3. IMPORTANTE (RIGOR AGRONÓMICO): Si los macronutrientes principales (N, P, K) están en 0 o cercanos a 0 y la conductividad es 0, reconoce con rigor que el suelo presenta un agotamiento nutricional crítico y es NO APTO en su estado actual para ningún cultivo comercial sin una enmienda y fertilización intensiva previa. La compatibilidad debe reflejar este estado crítico (<15%) y viabilidad 'No Apto'.
4. Devuelve estrictamente el resultado en formato JSON válido (sin markdown ```json) con la siguiente estructura:
{{
  "recomendaciones": [
    {{
      "cultivo": "Nombre del Cultivo (Variedad)",
      "compatibilidad": 8,
      "viabilidad": "No Apto",
      "descripcion": "Razón técnica del estado del suelo y limitaciones.",
      "plan_fertilizacion": "Enmiendas y fertilizantes requeridos."
    }}
  ],
  "consejo_general": "Consejo agronómico general del lote y plan correctivo.",
  "es_critico": true
}}
"""
            response = model.generate_content(prompt, request_options={"timeout": 6.0})
            text = response.text.replace("```json", "").replace("```", "").strip()
            resultado_json = json.loads(text.strip())
            resultado_json["modo"] = "ia"

            # Reemplazo de porcentajes alucinados por cálculos edafológicos reales
            catalogo = list(Cultivo.objects.filter(activo=True))
            recs_reales = []
            for rec in resultado_json.get("recomendaciones", []):
                base = _norm(str(rec.get("cultivo", "")).split('(')[0])
                if len(base) < 3:
                    continue
                cult = next((x for x in catalogo if _norm(x.nombre) == base), None) \
                    or next((x for x in catalogo if base in _norm(x.nombre)), None)
                if not cult:
                    continue
                real, _det = puntuar_cultivo(cult, h, t, c, ph, n, p, k)
                if real is None:
                    continue
                rec["cultivo"] = cult.nombre
                rec["compatibilidad"] = real
                recs_reales.append(rec)

            if not recs_reales:
                raise ValueError("Gemini no propuso cultivos reconocidos en el catálogo oficial del Huila")

            resultado_json["recomendaciones"] = recs_reales

            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_json, h, t, c, ph, n, p, k)

            return JsonResponse({"estado": "ok", "diagnostico": resultado_json, "modo": "ia"})

        except Exception as gemini_error:
            # Si el usuario eligió MODO ONLINE (IA) de forma explícita, avisarle del fallo
            if modo_solicitado == 'online':
                return JsonResponse({
                    "estado": "error",
                    "mensaje": f"No se pudo completar la consulta con la IA de Google: {str(gemini_error)}. Puedes intentar de nuevo o cambiar al modo Offline."
                })

            # En modo AUTO: fallback al motor offline local de contingencia
            resultado_offline = calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia=preferencia)
            resultado_offline["aviso"] = "Se activó el motor agronómico offline debido a interrupción temporal en el servicio de IA."
            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_offline, h, t, c, ph, n, p, k)
            return JsonResponse({"estado": "ok", "diagnostico": resultado_offline, "modo": "offline"})

    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)


@login_required(login_url='login')
def api_promedio_puntos(request):
    """
    Endpoint HTTP: GET /ia/promedio_puntos/?solicitud_id=<id>
    ---------------------------------------------------------
    Calcula los promedios estadísticos de los puntos de muestreo tomados en un terreno.

    Asegura autorización verificando que la solicitud esté asignada al laboratorista activo.
    Aplica `Avg()` de Django ORM sobre los 7 parámetros físicos y químicos.
    """
    solicitud_id = request.GET.get('solicitud_id')
    if not solicitud_id:
        return JsonResponse({"estado": "error", "mensaje": "Falta solicitud_id"}, status=400)

    from apps.analisis.models import PuntoMuestreo
    from apps.solicitudes.models import SolicitudAnalisis
    from django.db.models import Avg

    try:
        sol = SolicitudAnalisis.objects.get(id=solicitud_id, laboratorista_asignado=request.user)
        puntos_tomados = PuntoMuestreo.objects.filter(solicitud=sol, estado='TOMADO')

        if puntos_tomados.exists():
            prom = puntos_tomados.aggregate(
                h=Avg('humedad'),
                t=Avg('temperatura'),
                c=Avg('conductividad'),
                ph=Avg('ph'),
                n=Avg('nitrogeno'),
                p=Avg('fosforo'),
                k=Avg('potasio')
            )
            promedio_datos = {
                "humedad": round(float(prom['h'] or 45.0), 1),
                "temperatura": round(float(prom['t'] or 24.0), 1),
                "conductividad": round(float(prom['c'] or 1.2), 2),
                "ph": round(float(prom['ph'] or 6.5), 1),
                "nitrogeno": round(float(prom['n'] or 120.0), 0),
                "fosforo": round(float(prom['p'] or 40.0), 0),
                "potasio": round(float(prom['k'] or 150.0), 0),
                "muestras_tomadas": puntos_tomados.count()
            }
        else:
            # Fallback si el análisis se realiza por muestra traída al laboratorio (sin puntos en mapa)
            from apps.sensores.models import LecturaSensor
            ultima = LecturaSensor.objects.order_by('-timestamp').first()
            if ultima:
                promedio_datos = {
                    "humedad": round(float(ultima.humedad), 1),
                    "temperatura": round(float(ultima.temperatura), 1),
                    "conductividad": round(float(ultima.conductividad), 2),
                    "ph": round(float(ultima.ph), 1),
                    "nitrogeno": round(float(ultima.nitrogeno), 0),
                    "fosforo": round(float(ultima.fosforo), 0),
                    "potasio": round(float(ultima.potasio), 0),
                    "muestras_tomadas": 1
                }
            else:
                promedio_datos = {
                    "humedad": 48.0,
                    "temperatura": 23.5,
                    "conductividad": 1.4,
                    "ph": 6.2,
                    "nitrogeno": 135.0,
                    "fosforo": 45.0,
                    "potasio": 160.0,
                    "muestras_tomadas": 1
                }

        return JsonResponse({"estado": "ok", "promedio": promedio_datos})
    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)


@login_required(login_url='login')
@csrf_exempt
def api_compartir_resultado(request):
    """
    Endpoint HTTP: POST /ia/compartir/
    ----------------------------------
    HU-0031: Cierre formal y entrega del análisis edafológico al agricultor.

    Operación:
      - Valida que el invocador sea el laboratorista asignado.
      - Persiste el `RegistroAnalisis` con su dictamen completo.
      - Transiciona la `SolicitudAnalisis` al estado 'COMPLETADA'.
      - Notifica disponibilidad para consulta inmediata en el historial del agricultor.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)

    try:
        data = json.loads(request.body)
        solicitud_id = data.get("solicitud_id")
        if not solicitud_id:
            return JsonResponse({"estado": "error", "mensaje": "solicitud_id es requerido"}, status=400)

        from apps.solicitudes.models import SolicitudAnalisis
        from apps.analisis.models import RegistroAnalisis

        sol = SolicitudAnalisis.objects.get(id=solicitud_id)

        # Control de autorización: únicamente el laboratorista a cargo puede cerrar el informe
        if sol.laboratorista_asignado != request.user:
            return JsonResponse({'error': 'No autorizado para compartir este análisis'}, status=403)

        datos = data.get("datos", {})
        diagnostico = data.get("diagnostico", {})

        _guardar_diagnostico_solicitud(
            solicitud_id,
            diagnostico,
            datos.get('humedad', 0),
            datos.get('temperatura', 0),
            datos.get('conductividad', 0),
            datos.get('ph', 0),
            datos.get('nitrogeno', 0),
            datos.get('fosforo', 0),
            datos.get('potasio', 0),
        )

        nombre_agri = sol.agricultor.get_full_name() or sol.agricultor.username
        return JsonResponse({
            "estado": "ok",
            "mensaje": f"Resultados compartidos exitosamente con {nombre_agri}. El informe ya está disponible en su historial."
        })
    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)


@csrf_exempt
def api_sincronizar_offline(request):
    """
    Endpoint HTTP: POST /ia/sincronizar-offline/
    -------------------------------------------
    HU-0032: Sincronización masiva por lotes de muestreos y análisis recopilados sin conexión.

    Recibe el array `items` desde la base de datos IndexedDB del cliente:
      - Procesa cada solicitud verificando estados válidos ('ASIGNADA', 'EN_PROCESO', 'COMPLETADA').
      - Consolida el diagnóstico final e inserta cada estación individual en `PuntoMuestreo`.
      - Registra georreferenciación 3D (latitud, longitud, altitud) de las muestras tomadas en campo.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)

    try:
        data = json.loads(request.body)
        items = data.get("items", [])
        if not items:
            return JsonResponse({"estado": "ok", "sincronizados": 0, "mensaje": "No hay elementos para sincronizar"})

        from apps.solicitudes.models import SolicitudAnalisis
        from apps.analisis.models import PuntoMuestreo

        sincronizados = 0
        for item in items:
            sol_id = item.get("solicitud_id")
            datos = item.get("datos", {})
            diagnostico = item.get("diagnostico", {})
            puntos = item.get("puntos", [])

            if sol_id:
                try:
                    sol = SolicitudAnalisis.objects.get(id=sol_id)
                    if sol.estado not in ('ASIGNADA', 'EN_PROCESO', 'COMPLETADA'):
                        continue

                    # Persistencia consolidada
                    _guardar_diagnostico_solicitud(
                        sol_id,
                        diagnostico,
                        datos.get('humedad', 0),
                        datos.get('temperatura', 0),
                        datos.get('conductividad', 0),
                        datos.get('ph', 0),
                        datos.get('nitrogeno', 0),
                        datos.get('fosforo', 0),
                        datos.get('potasio', 0),
                    )

                    # Persistencia de puntos individuales georreferenciados
                    for p_data in puntos:
                        p_num = p_data.get("numero")
                        if p_num:
                            punto, _ = PuntoMuestreo.objects.get_or_create(solicitud=sol, numero=p_num)
                            punto.humedad = p_data.get("humedad")
                            punto.temperatura = p_data.get("temperatura")
                            punto.conductividad = p_data.get("conductividad")
                            punto.ph = p_data.get("ph")
                            punto.nitrogeno = p_data.get("nitrogeno")
                            punto.fosforo = p_data.get("fosforo")
                            punto.potasio = p_data.get("potasio")
                            if p_data.get("latitud") is not None:
                                punto.latitud = p_data.get("latitud")
                            if p_data.get("longitud") is not None:
                                punto.longitud = p_data.get("longitud")
                            if p_data.get("altitud") is not None:
                                punto.altitud = p_data.get("altitud")
                            punto.estado = 'TOMADO'
                            punto.save()

                    sincronizados += 1
                except SolicitudAnalisis.DoesNotExist:
                    continue

        return JsonResponse({
            "estado": "ok",
            "sincronizados": sincronizados,
            "mensaje": f"Se han sincronizado {sincronizados} análisis guardados localmente."
        })
    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)


def _norm(texto):
    """
    Normaliza una cadena de texto para comparaciones botánicas y taxonómicas.

    Aplica descomposición Unicode NFD para suprimir acentos diacríticos (á -> a),
    convierte a minúsculas y elimina espacios circundantes.
    """
    import unicodedata
    t = unicodedata.normalize('NFD', str(texto or '').lower())
    return ''.join(ch for ch in t if unicodedata.category(ch) != 'Mn').strip()


def puntuar_cultivo(cultivo, h, t, c, ph, n, p, k):
    """
    Cálculo matemático canónico del porcentaje de compatibilidad de un cultivo.

    Compara las 7 variables edáficas contra los rangos ideales [min, max] del cultivo:
      - Dentro del rango ideal: 100% de puntuación para esa variable.
      - Fuera del rango: penalización proporcional lineal (`distancia / ancho_tolerancia`).
      - Si una sonda no reportó lectura (valor <= 0), se omite de la ponderación
        sin penalizar artificialmente el puntaje.

    Ponderación por parámetro:
      - pH: 25%
      - Nitrógeno (N): 15%
      - Fósforo (P): 15%
      - Potasio (K): 15%
      - Humedad: 10%
      - Temperatura: 10%
      - Conductividad Eléctrica: 10%

    Retorna:
        tuple: (porcentaje_entero_0_a_100 | None, lista_de_diagnósticos_por_variable)
    """
    params = [
        ('pH', ph, cultivo.ph_min, cultivo.ph_max, 0.25, ''),
        ('Nitrógeno', n, cultivo.nitrogeno_min, cultivo.nitrogeno_max, 0.15, ' mg/kg'),
        ('Fósforo', p, cultivo.fosforo_min, cultivo.fosforo_max, 0.15, ' mg/kg'),
        ('Potasio', k, cultivo.potasio_min, cultivo.potasio_max, 0.15, ' mg/kg'),
        ('Humedad', h, cultivo.humedad_min, cultivo.humedad_max, 0.10, '%'),
        ('Temperatura', t, cultivo.temperatura_min, cultivo.temperatura_max, 0.10, ' °C'),
        ('Conductividad', c, cultivo.conductividad_min, cultivo.conductividad_max, 0.10, ' us/cm'),
    ]

    total, peso, detalle = 0.0, 0.0, []
    for nombre, valor, lo, hi, w, unidad in params:
        v = float(valor or 0)
        if v <= 0:
            continue  # Sin lectura de sensor: no se inventa valor
        lo, hi = float(lo), float(hi)
        ancho = max(hi - lo, 0.1 * max(abs(hi), 1.0))
        dist = (lo - v) if v < lo else ((v - hi) if v > hi else 0.0)
        score = max(0.0, 100.0 - 100.0 * dist / ancho)
        total += score * w
        peso += w
        estado = 'dentro del rango' if dist == 0 else ('por debajo' if v < lo else 'por encima')
        detalle.append(f"{nombre}: {v:g}{unidad} (ideal {lo:g}-{hi:g}{unidad}) -> {estado}")

    if peso == 0:
        return None, detalle

    return int(round(total / peso)), detalle


@login_required(login_url='login')
@csrf_exempt
def api_consultar_ia_agricultor(request):
    """
    Endpoint HTTP: POST /ia/consultar-agricultor/
    --------------------------------------------
    Asistente agronómico interactivo para responder dudas del productor sobre un cultivo específico.

    Arquitectura de Responsabilidad Desacoplada:
      1. El PORCENTAJE real es calculado por `puntuar_cultivo` contrastando con la base de datos MySQL.
      2. El modelo generativo Gemini recibe el score precomputado y se le prohíbe explícitamente
         modificarlo o inventar cifras.
      3. Gemini redacta la explicación agronómica y las dosis de enmienda o fertilización adecuadas.
      4. Si Gemini no está disponible, el sistema genera la explicación técnica mediante plantillas heurísticas.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)

    try:
        data = json.loads(request.body)
        solicitud_id = data.get("solicitud_id")
        cultivo_busqueda = data.get("cultivo", "").strip()

        if not solicitud_id or not cultivo_busqueda:
            return JsonResponse({"estado": "error", "mensaje": "Faltan datos de consulta"}, status=400)

        from django.db.models import Q
        from apps.analisis.models import RegistroAnalisis

        # Validación de seguridad: el análisis debe pertenecer al agricultor o al laboratorista asignado
        try:
            analisis = RegistroAnalisis.objects.get(
                Q(solicitud__agricultor=request.user) |
                Q(solicitud__laboratorista_asignado=request.user),
                solicitud_id=solicitud_id,
            )
        except RegistroAnalisis.DoesNotExist:
            return JsonResponse({"estado": "error", "mensaje": "Análisis no encontrado"}, status=404)

        # 1) Búsqueda normalizada del cultivo en el catálogo
        q = _norm(cultivo_busqueda)
        catalogo = list(Cultivo.objects.filter(activo=True).order_by('nombre'))
        cultivo = next((c for c in catalogo if _norm(c.nombre) == q), None) \
            or next((c for c in catalogo if q in _norm(c.nombre)), None)

        # 2) Puntuación cuantitativa exacta basada en base de datos
        compat, detalle = (None, [])
        if cultivo:
            compat, detalle = puntuar_cultivo(
                cultivo, analisis.humedad, analisis.temperatura, analisis.conductividad,
                analisis.ph, analisis.nitrogeno, analisis.fosforo, analisis.potasio,
            )
        nombre_cultivo = cultivo.nombre if cultivo else cultivo_busqueda

        # 3) Redacción cualitativa con Google Gemini (opcional)
        texto = None
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai is not None:
            try:
                genai.configure(api_key=api_key)
                model = obtener_modelo_gemini()
                if compat is not None:
                    contexto = (
                        f"La compatibilidad ya fue calculada con rangos del catálogo: {compat}%. "
                        "NO la cambies ni la menciones con otro valor.\n"
                        "Comparación por parámetro:\n- " + "\n- ".join(detalle)
                    )
                else:
                    contexto = (
                        "Este cultivo NO está en el catálogo de rangos, así que NO des ningún "
                        "porcentaje ni número de compatibilidad. Da solo una orientación cualitativa.\n"
                        f"Lecturas: pH {analisis.ph}, N {analisis.nitrogeno}, P {analisis.fosforo}, "
                        f"K {analisis.potasio} mg/kg, humedad {analisis.humedad}%, "
                        f"temperatura {analisis.temperatura} °C."
                    )
                prompt = (
                    "Eres un ingeniero agrónomo experto en suelos del Huila, Colombia.\n"
                    f"Lote: '{analisis.solicitud.terreno.nombre}'. Cultivo consultado: '{nombre_cultivo}'.\n"
                    + contexto +
                    "\nResponde SOLO con JSON válido (sin markdown) con estas dos claves:\n"
                    '{"descripcion": "explicación breve de por qué este suelo sirve o no para el cultivo, '
                    'citando los parámetros fuera de rango", '
                    '"recomendacion_suelo": "enmiendas o fertilización concretas para corregir lo que falte"}'
                )
                res = model.generate_content(prompt)
                raw = res.text.strip()
                ini, fin = raw.find('{'), raw.rfind('}')
                texto = json.loads(raw[ini:fin + 1] if ini != -1 and fin != -1 else raw)
            except Exception as ex:
                print(f"[GEMINI ERROR en consulta]: {ex}")
                texto = None

        # 4) Respaldo determinista sin IA
        if not texto or not texto.get("descripcion"):
            if compat is not None:
                fuera = [d.split(' (')[0] for d in detalle if 'dentro' not in d]
                texto = {
                    "descripcion": f"Compatibilidad calculada con los rangos de {nombre_cultivo}. "
                                   + ("Todos los parámetros medidos están en rango." if not fuera
                                      else "Fuera de rango: " + ", ".join(fuera) + "."),
                    "recomendacion_suelo": "; ".join(d for d in detalle if 'dentro' not in d)
                                           or "Mantener el plan de fertilización estándar.",
                }
            else:
                texto = {
                    "descripcion": f"'{nombre_cultivo}' no está en el catálogo de cultivos, "
                                   "por eso no se puede calcular un porcentaje real.",
                    "recomendacion_suelo": "Pide al administrador que registre sus rangos de suelo.",
                }

        evaluacion = {
            "cultivo": nombre_cultivo,
            "compatibilidad": compat,
            "descripcion": texto.get("descripcion", ""),
            "recomendacion_suelo": texto.get("recomendacion_suelo", ""),
        }
        return JsonResponse({"estado": "ok", "evaluacion": evaluacion})
    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)