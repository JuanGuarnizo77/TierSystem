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
import logging
import os
import socket
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from apps.cultivos.models import Cultivo
from core.permissions import tiene_rol
from core.utils import registrar_evento_seguridad, verificar_rate_limit

logger = logging.getLogger(__name__)

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


def _validar_parametros_suelo(h, t, c, ph, n, p, k):
    """
    Valida en el servidor que los 7 parámetros fisicoquímicos se encuentren dentro
    de rangos físicamente posibles, previniendo inyección de valores corruptos o extremos.
    """
    try:
        h, t, c, ph, n, p, k = float(h), float(t), float(c), float(ph), float(n), float(p), float(k)
    except (TypeError, ValueError):
        return False, "Todos los parámetros del suelo deben ser valores numéricos válidos."

    if not (0.0 <= h <= 100.0):
        return False, "La humedad debe estar entre 0% y 100%."
    if not (-30.0 <= t <= 85.0):
        return False, "La temperatura está fuera de un rango físico válido (-30°C a 85°C)."
    if not (0.0 <= ph <= 14.0):
        return False, "El pH debe estar en la escala de 0 a 14."
    if c < 0.0 or c > 50000.0:
        return False, "La conductividad eléctrica no puede ser negativa ni exceder el límite físico."
    if n < 0.0 or p < 0.0 or k < 0.0 or n > 10000.0 or p > 10000.0 or k > 10000.0:
        return False, "Los macronutrientes N, P y K deben estar entre 0 y 10000 mg/kg."
    return True, None


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
    if not isinstance(recs, list):
        return

    for rec in recs[:10]:
        if not isinstance(rec, dict):
            continue
        nombre = str(rec.get("cultivo", "Cultivo"))[:120]
        # Limpieza de posibles paréntesis descriptivos (ej. "Café (Castillo)" -> "Café")
        nombre_limpio = nombre.split('(')[0].strip()
        try:
            compat = max(0.0, min(100.0, float(rec.get("compatibilidad", 0.0))))
        except (TypeError, ValueError):
            compat = 0.0
        desc = str(rec.get("descripcion", ""))[:2000]
        plan = str(rec.get("plan_fertilizacion", ""))[:2000]

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
    from apps.solicitudes.views import _evaluar_parametros_agronomicos
    from django.utils import timezone

    try:
        sol = SolicitudAnalisis.objects.get(id=solicitud_id)
    except SolicitudAnalisis.DoesNotExist:
        return None

    # Preparar copia enriquecida con snapshot congelado de rangos (US-0037) y trazabilidad de origen
    diag_dict = dict(diagnostico) if isinstance(diagnostico, dict) else {"consejo_general": str(diagnostico)}
    modo_str = str(diag_dict.get('modo', 'ia')).lower()
    origen_diag = 'LOCAL' if modo_str == 'offline' else 'IA'
    pendiente_ia = bool(origen_diag == 'LOCAL')

    class _DummyAnalisis:
        pass

    dummy = _DummyAnalisis()
    dummy.humedad = h
    dummy.temperatura = t
    dummy.conductividad = c
    dummy.ph = ph
    dummy.nitrogeno = n
    dummy.fosforo = p
    dummy.potasio = k
    dummy.diagnostico_ia = json.dumps(
        {k_d: v_d for k_d, v_d in diag_dict.items() if k_d != 'evaluacion_congelada'},
        ensure_ascii=False
    )
    dummy._ignorar_snapshot = True

    try:
        snapshot = _evaluar_parametros_agronomicos(dummy, sol.cultivo_deseado)
        diag_dict['evaluacion_congelada'] = snapshot
        compat_deseado = float(snapshot.get('compatibilidad', 0.0))
    except Exception:
        compat_deseado = None
        if diag_dict.get('recomendaciones') and isinstance(diag_dict['recomendaciones'], list):
            try:
                compat_deseado = float(diag_dict['recomendaciones'][0].get('compatibilidad', 0.0))
            except Exception:
                compat_deseado = None

    # Persistencia o actualización atómica del informe consolidado dentro de una transacción
    with transaction.atomic():
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
                'origen_diagnostico': origen_diag,
                'pendiente_reenvio_ia': pendiente_ia,
                'compatibilidad_cultivo_deseado': compat_deseado,
                'diagnostico_ia': json.dumps(diag_dict, ensure_ascii=False),
            }
        )

        # Transición definitiva del ciclo de atención con estampa de finalización
        sol.estado = 'COMPLETADA'
        if not sol.fecha_finalizacion:
            sol.fecha_finalizacion = timezone.now()
        sol.save()

        # Sincronización en tabla hija de recomendaciones
        _guardar_recomendaciones_relacionales(registro, diag_dict)

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


def _homologar_conductividad_dsm(c_valor, c_max_catalogo=2.5):
    """
    Homologa la lectura de Conductividad Eléctrica (CE) a dS/m (decisiemens por metro).

    Las sondas RS485 Modbus 7 en 1 reportan la CE bruta en µS/cm (ej. 80 - 2500 µS/cm),
    mientras que los umbrales agronómicos del catálogo (`Cultivo`) están expresados en dS/m
    (1 dS/m = 1000 µS/cm). Si el valor medido está en escala de µS/cm (> 15.0) y el umbral
    del catálogo está en dS/m (<= 15.0), realiza la conversión física exacta dividiendo por 1000.
    """
    c_val = float(c_valor or 0.0)
    c_max = float(c_max_catalogo or 2.5)
    if c_val <= 0:
        return 0.0
    if c_max <= 15.0 and c_val > 15.0:
        return round(c_val / 1000.0, 4)
    return c_val


def _evaluar_npk_sonda_7en1(valor, min_cat, max_cat, humedad, tipo='n'):
    """
    Evalúa las lecturas de N, P y K considerando el principio físico real de la sonda RS485 7 en 1.

    Fundamento técnico:
      - Las sondas dieléctricas/conductimétricas 7 en 1 NO realizan extracción química total de
        laboratorio (como Bray II, Kjeldahl o Acetato de Amonio, cuyos rangos de 100-300 mg/kg
        figuran en la literatura). En su lugar, estiman el NPK disponible en función de la
        Conductividad Eléctrica (CE) de los iones libres disueltos en el agua del poro.
      - En suelos agrícolas naturales con plantas o plántulas activas (ej. café en crecimiento)
        y reserva orgánica (CIC), la concentración de iones libres en solución sin fertilización
        salina reciente suele oscilar entre el 20% y el 35% del umbral de laboratorio, y el
        Fósforo (P) se fija fuertemente a coloides de Fe/Al/Ca aportando muy poca conductividad.
      - Cuando la humedad volumétrica es inferior a la capacidad de campo (< 55%), la disociación
        iónica disminuye, por lo que se aplica un factor de compensación hidro-conductimétrico.
    """
    v = float(valor or 0.0)
    lo = max(float(min_cat or 1.0), 1.0)
    hi = max(float(max_cat or lo), lo)
    h = float(humedad or 0.0)

    if v <= 0:
        return 0.0

    # Factor de compensación por baja humedad (menor agua libre = menor lectura conductimétrica de iones)
    factor_hum = 1.0
    if 0.0 < h < 55.0:
        factor_hum = 1.0 + ((55.0 - h) / 55.0) * 0.55
    v_efectivo = v * factor_hum

    # Umbral de suficiencia iónica en solución para sonda 7 en 1 in-situ
    # El fósforo presenta alta adsorción coloidal en suelos cafeteros del Huila (20% del rango lab)
    ratio_soluble = 0.20 if tipo == 'p' else 0.25
    umbral_sonda = max(6.0 if tipo == 'p' else 15.0, lo * ratio_soluble)

    if lo <= v <= hi or (v_efectivo >= lo and v <= hi):
        return 100.0
    elif v > hi:
        return max(45.0, 100.0 - ((v - hi) / hi) * 40.0)
    elif v_efectivo >= umbral_sonda:
        # Reserva soluble activa en suelo natural: puntaje alto (82% a 98%), requiere solo abonado de sostén
        progreso = (v_efectivo - umbral_sonda) / max(lo - umbral_sonda, 1.0)
        return min(98.0, 82.0 + progreso * 16.0)
    else:
        # Suelo con baja concentración iónica soluble pero biológicamente viable con plan de fertilización
        return max(55.0, 55.0 + (v_efectivo / max(umbral_sonda, 1.0)) * 27.0)


def _evaluar_ce_sonda_7en1(c_raw, c_min_cat, c_max_cat):
    """
    Evalúa la Conductividad Eléctrica (CE) homologando unidades (µS/cm -> dS/m).

    En suelos naturales y plántulas (como almácigos o lotes jóvenes de café), una CE baja
    (0.05 - 0.8 dS/m, equivalente a 50 - 800 µS/cm) indica ausencia de estrés salino y
    protege las raíces jóvenes, por lo que no debe penalizarse como inviable.
    """
    c_raw_f = float(c_raw or 0.0)
    if c_raw_f <= 0:
        return 0.0, 0.0
    c_min = float(c_min_cat or 0.5)
    c_max = float(c_max_cat or 2.5)
    c_dsm = _homologar_conductividad_dsm(c_raw_f, c_max)

    if c_min <= c_dsm <= c_max:
        return 100.0, c_dsm
    elif c_dsm < c_min:
        # Baja salinidad: segura para raíces y plántulas; indica baja carga de sales disueltas
        return min(95.0, 78.0 + (c_dsm / max(c_min, 0.1)) * 17.0), c_dsm
    else:
        # Exceso de salinidad: riesgo osmótico real para las raíces
        return max(15.0, 100.0 - ((c_dsm - c_max) / max(c_max, 0.1)) * 75.0), c_dsm


def calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia='', altitud=None):
    """
    Motor Agronómico Edafológico Determinista y Offline de TierSystem.

    Evalúa matemáticamente las lecturas de suelo contra los umbrales fisiológicos de los
    cultivos registrados en `cultivos_cultivo`, calibrado para sondas RS485 7 en 1.
    Separa la aptitud edafoclimática del terreno (pH, Temperatura, Humedad, Altitud) de la
    concentración instantánea de iones solubles (NPK/CE), evitando falsos rechazos en suelos
    fértiles naturales donde crecen plantas activas sin fertilización salina reciente.

    Ponderaciones del Algoritmo Edafoclimático:
      - pH: 30% (variable maestra de absorción radicular y disponibilidad química).
      - Temperatura: 15% (adaptación bioclimática y tasa metabólica).
      - Humedad: 15% (disponibilidad de solución acuosa en el poro del suelo).
      - Nitrógeno (N): 10% (estimación iónica compensada por humedad).
      - Fósforo (P): 10% (estimación iónica ajustada por fijación coloidal).
      - Potasio (K): 10% (estimación iónica en solución).
      - Conductividad Eléctrica (CE): 10% (homologada en dS/m, control de salinidad).
      - Altitud: 15% (adaptación a pisos térmicos del Huila, si está disponible).

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

    # Condición de sustrato inerte / sonda en el aire (solo crítico cuando NPK y CE son nulos o suelo seco estéril)
    es_suelo_critico = (n <= 0 and p <= 0 and k <= 0 and c <= 0) or (n <= 1 and p <= 1 and k <= 1 and c <= 2 and h < 8.0)

    for cultivo in cultivos:
        puntajes = []
        # ---------------------------------------------------------------------
        # 1. Evaluación de pH (Ponderación: 30% - Variable maestra edáfica)
        # ---------------------------------------------------------------------
        ph_min = float(cultivo.ph_min)
        ph_max = float(cultivo.ph_max)
        if ph > 0:
            if ph_min <= ph <= ph_max:
                score_ph = 100.0
            elif ph < ph_min:
                diff = ph_min - ph
                score_ph = max(10.0, 100.0 - (diff / 1.5) * 75.0)
            else:
                diff = ph - ph_max
                score_ph = max(10.0, 100.0 - (diff / 1.5) * 75.0)
            puntajes.append(('ph', score_ph, 0.30))

        # ---------------------------------------------------------------------
        # 2. Evaluación de NPK con curva para Sonda 7 en 1 (10% c/u = 30%)
        # ---------------------------------------------------------------------
        n_min, n_max = float(cultivo.nitrogeno_min), float(cultivo.nitrogeno_max)
        score_n = _evaluar_npk_sonda_7en1(n, n_min, n_max, h, tipo='n')
        puntajes.append(('n', score_n, 0.10))

        p_min, p_max = float(cultivo.fosforo_min), float(cultivo.fosforo_max)
        score_p = _evaluar_npk_sonda_7en1(p, p_min, p_max, h, tipo='p')
        puntajes.append(('p', score_p, 0.10))

        k_min, k_max = float(cultivo.potasio_min), float(cultivo.potasio_max)
        score_k = _evaluar_npk_sonda_7en1(k, k_min, k_max, h, tipo='k')
        puntajes.append(('k', score_k, 0.10))

        # ---------------------------------------------------------------------
        # 3. Conductividad Eléctrica CE homologada a dS/m (Ponderación: 10%)
        # ---------------------------------------------------------------------
        c_min = float(cultivo.conductividad_min)
        c_max = float(cultivo.conductividad_max)
        score_c, c_dsm = _evaluar_ce_sonda_7en1(c, c_min, c_max)
        puntajes.append(('c', score_c, 0.10))

        # ---------------------------------------------------------------------
        # 4. Humedad y Temperatura (Ponderación: 15% c/u)
        # ---------------------------------------------------------------------
        h_min = float(cultivo.humedad_min)
        h_max = float(cultivo.humedad_max)
        if h > 0:
            if h < h_min:
                score_h = max(35.0, (h / max(h_min, 1.0)) * 90.0)
            elif h_min <= h <= h_max:
                score_h = 100.0
            else:
                score_h = max(30.0, 100.0 - ((h - h_max) / max(h_max, 1.0)) * 50.0)
            puntajes.append(('h', score_h, 0.15))

        t_min = float(cultivo.temperatura_min)
        t_max = float(cultivo.temperatura_max)
        if t > 0:
            if t_min <= t <= t_max:
                score_t = 100.0
            else:
                diff_t = (t_min - t) if t < t_min else (t - t_max)
                score_t = max(25.0, 100.0 - (diff_t / 8.0) * 70.0)
            puntajes.append(('t', score_t, 0.15))

        # ---------------------------------------------------------------------
        # 5. Piso Altitudinal msnm (Ponderación: 15%)
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
            peso_total = sum(p_item[2] for p_item in puntajes)
            compatibilidad = sum(p_item[1] * p_item[2] for p_item in puntajes) / peso_total
        else:
            compatibilidad = 10.0

        if es_suelo_critico:
            compatibilidad = min(compatibilidad, 12.0)

        compat_final = round(float(compatibilidad), 1)

        # Construcción de planes agronómicos de fertilización correctiva y explicación de sonda
        planes = []
        if es_suelo_critico:
            planes.append("Déficit nutricional crítico total: N, P y K en 0 mg/kg con conductividad nula. Suelo inerte o sonda sin contacto húmedo. Requiere acondicionamiento orgánico de fondo, riego a capacidad de campo y fertilización compuesta NPK antes de sembrar.")
        else:
            if 0 < h < 45.0:
                planes.append(f"Humedad moderada/baja ({h:.1f}%): la sonda 7 en 1 mide iones disueltos por conductividad; al regar a capacidad de campo (55-65%) aumentará la disponibilidad iónica de NPK.")
            if ph > 0 and ph < ph_min:
                planes.append("Aplicar enmienda calcárea (Cal Dolomita o Cal Agrícola) para corregir acidez.")
            elif ph > ph_max:
                planes.append("Incorporar materia orgánica humificada para amortiguar el pH.")
            if n < n_min * 0.25:
                planes.append("Aportar Nitrógeno mediante abono orgánico (humus/compost) o fertilización nitrogenada fraccionada para sostener el crecimiento vegetativo.")
            elif n < n_min:
                planes.append("Reserva soluble de Nitrógeno moderada: acompañar con abonado orgánico de mantenimiento.")
            if p < p_min * 0.20:
                planes.append("Aplicar Fósforo localizado (DAP, roca fosfórica o micorrizas) para fortalecer el sistema radicular (el P suele fijarse en coloides del suelo).")
            if k < k_min * 0.25:
                planes.append("Suplir Potasio (KCl o Sulfato de Potasio) según etapa de desarrollo del cultivo.")
            if not planes:
                planes.append("Condiciones edafoclimáticas y nutricionales óptimas. Mantener plan de fertilización estándar.")

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
        compat_custom = 12.0 if es_suelo_critico else 72.0
        viab_custom = "No Apto" if compat_custom < 25 else ("Baja" if compat_custom < 50 else "Media")
        evaluaciones.insert(0, {
            "cultivo": preferencia.strip(),
            "compatibilidad": compat_custom,
            "viabilidad": viab_custom,
            "descripcion": f"Cultivo consultado específicamente por el usuario ({preferencia.strip()}).",
            "plan_fertilizacion": f"Déficit nutricional crítico total: N, P y K en 0 mg/kg. Suelo no viable para siembra de {preferencia.strip()}. Requiere acondicionamiento orgánico de fondo y fertilización compuesta NPK completa antes de cualquier siembra." if es_suelo_critico else f"Suelo con aptitud física para {preferencia.strip()}; acompañar con plan de nutrición orgánica y NPK gradual.",
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
            consejos.append(f"El suelo presenta acidez (pH {ph:.1f}), condición típica de zonas cafeteras del Huila.")
        elif ph > 7.5:
            consejos.append(f"El suelo es ligeramente alcalino (pH {ph:.1f}). Monitorear microelementos.")
        else:
            consejos.append(f"El pH ({ph:.1f}) se encuentra en un rango excelente para cultivos del Huila.")

        if n > 0 or p > 0 or k > 0:
            consejos.append(
                f"Lectura de iones solubles en sonda 7 en 1: N={n:.0f}, P={p:.0f}, K={k:.0f} mg/kg (CE={c:g} µS/cm). "
                "Recuerda que la sonda mide nutrientes disueltos en el agua del poro; valores bajos-moderados en tierra con plantas activas indican baja salinidad libre y responden muy bien a fertilización de mantenimiento."
            )

    consejos.append("Diagnóstico agronómico generado en modo offline (Motor Huila calibrado para sonda RS485 7 en 1).")

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
      1. Verifica permisos de rol ('LABORATORISTA' o 'ADMIN') y valida rangos en servidor.
      2. Extrae los 7 parámetros de suelo y la preferencia agronómica del usuario.
      3. Si se provee `solicitud_id`, verifica que pertenezca al laboratorista asignado (prevención IDOR/BOLA).
      4. Si se fuerza `modo == 'offline'`, ejecuta inmediatamente `calcular_diagnostico_edafologico`.
      5. Si `modo == 'auto'` y hay API Key de Gemini:
           a. Construye el prompt agronómico con restricciones estrictas.
           b. Invoca Google Gemini Flash con parsing JSON.
           c. Inyecta los porcentajes reales calculados por `puntuar_cultivo`, asegurando que
              la IA nunca invente o alucine porcentajes de compatibilidad.
           d. Si Gemini falla o excede el timeout, conmuta automáticamente al motor offline.
      6. Si se provee `solicitud_id` autorizado, persiste los resultados en base de datos.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)

    if not tiene_rol(request.user, 'LABORATORISTA', 'ADMIN'):
        registrar_evento_seguridad(
            'DIAGNOSTICO_IA_NO_AUTORIZADO',
            request=request,
            nivel='WARNING',
            detalle='Intento de acceso a api_diagnosticar_ia sin rol LABORATORISTA/ADMIN.'
        )
        return JsonResponse({"estado": "error", "mensaje": "No autorizado para ejecutar diagnósticos de laboratorio."}, status=403)

    if not verificar_rate_limit(request, 'ia_diagnosticar', max_requests=30, window_seconds=60):
        return JsonResponse({"estado": "error", "mensaje": "Demasiadas solicitudes de diagnóstico. Espera un minuto."}, status=429)

    try:
        data = json.loads(request.body)
        h = float(data.get("humedad", 0) or 0)
        t = float(data.get("temperatura", 0) or 0)
        c = float(data.get("conductividad", 0) or 0)
        ph = float(data.get("ph", 0) or 0)
        n = float(data.get("nitrogeno", 0) or 0)
        p = float(data.get("fosforo", 0) or 0)
        k = float(data.get("potasio", 0) or 0)

        es_valido_rango, msg_rango = _validar_parametros_suelo(h, t, c, ph, n, p, k)
        if not es_valido_rango:
            return JsonResponse({"estado": "error", "mensaje": msg_rango}, status=400)

        solicitud_id = data.get("solicitud_id")
        preferencia = str(data.get("preferencia", "")).strip()[:100]
        modo_solicitado = str(data.get("modo", "auto")).strip().lower()
        if modo_solicitado not in ('auto', 'online', 'offline'):
            modo_solicitado = 'auto'

        # Control de acceso contra IDOR/BOLA: verificar titularidad técnica de la solicitud antes de modificarla
        if solicitud_id:
            from apps.solicitudes.models import SolicitudAnalisis
            try:
                sol_check = SolicitudAnalisis.objects.get(id=solicitud_id)
            except (SolicitudAnalisis.DoesNotExist, ValueError, TypeError):
                return JsonResponse({"estado": "error", "mensaje": "Solicitud no encontrada."}, status=404)

            if not tiene_rol(request.user, 'ADMIN') and sol_check.laboratorista_asignado_id != request.user.id:
                registrar_evento_seguridad(
                    'IDOR_BLOQUEADO_DIAGNOSTICAR',
                    request=request,
                    nivel='WARNING',
                    detalle=f"Intento de sobrescribir solicitud #{solicitud_id} asignada a otro técnico."
                )
                return JsonResponse({"estado": "error", "mensaje": "No autorizado para registrar diagnóstico en esta solicitud."}, status=403)

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
                    "mensaje": "El servicio de IA en la nube no está configurado actualmente."
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
2. Propón 1 o 2 cultivos ideales (incluye su variedad si aplica, ej: Café Borbón, Café Castillo, Maíz Amarillo). {prompt_preferencia}
3. IMPORTANTE (CALIBRACIÓN PARA SONDA IN-SITU 7 EN 1):
   - Las lecturas provienen de una sonda RS485 (sensor 7 en 1) que mide la solución acuosa del suelo y estima NPK por conductividad de iones libres.
   - En suelos agrícolas con plantas vivas o plántulas en crecimiento (como café), es NORMAL registrar valores de NPK libre moderados (15 a 60 mg/kg) y conductividad baja/media (50 a 400 µS/cm) sin que el suelo sea estéril. La viabilidad de establecimiento depende del pH, humedad, temperatura y altitud. Los niveles de NPK indican el plan de fertilización de mantenimiento, NO la imposibilidad de cultivar.
   - Si pH, humedad y temperatura son aptos para el cultivo (ej. café con pH 5.0-6.2 y clima templado), la viabilidad debe ser Alta o Media con plan de fertilización de soporte.
   - SOLO declara el suelo como 'No Apto' si N, P, K y conductividad están todos en 0 absoluto (suelo inerte o sensor al aire) o si el pH es extremo (< 4.0 o > 8.5).
4. Devuelve estrictamente el resultado en formato JSON válido (sin markdown ```json) con la siguiente estructura:
{{
  "recomendaciones": [
    {{
      "cultivo": "Nombre del Cultivo (Variedad)",
      "compatibilidad": 88,
      "viabilidad": "Alta",
      "descripcion": "Razón técnica del estado del suelo y potencial agroecológico.",
      "plan_fertilizacion": "Enmiendas y fertilizantes requeridos."
    }}
  ],
  "consejo_general": "Consejo agronómico general del lote y plan correctivo.",
  "es_critico": false
}}
"""
            response = model.generate_content(prompt, request_options={"timeout": 6.0})
            text = response.text.replace("```json", "").replace("```", "").strip()
            resultado_json = json.loads(text.strip())
            resultado_json["modo"] = "ia"
            # Rigor agronómico: es_critico solo es True si los macronutrientes NPK y CE están nulos o en 0 absoluto
            resultado_json["es_critico"] = bool((n <= 0 and p <= 0 and k <= 0 and c <= 0) or (n <= 1 and p <= 1 and k <= 1 and c <= 2 and h < 8.0))

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
            logger.warning("Fallo en consulta a Gemini en api_diagnosticar_ia: %s", gemini_error)
            # Si el usuario eligió MODO ONLINE (IA) de forma explícita, avisarle del fallo sin exponer trazas internas
            if modo_solicitado == 'online':
                return JsonResponse({
                    "estado": "error",
                    "mensaje": "No se pudo completar la consulta con el servicio de IA en este momento. Puedes intentar de nuevo o cambiar al modo Offline."
                })

            # En modo AUTO: fallback al motor offline local de contingencia
            resultado_offline = calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia=preferencia)
            resultado_offline["aviso"] = "Se activó el motor agronómico offline debido a interrupción temporal en el servicio de IA."
            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_offline, h, t, c, ph, n, p, k)
            return JsonResponse({"estado": "ok", "diagnostico": resultado_offline, "modo": "offline"})

    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"estado": "error", "mensaje": "Formato de datos de entrada inválido."}, status=400)
    except Exception as e:
        logger.error("Error interno en api_diagnosticar_ia: %s", e, exc_info=True)
        return JsonResponse({"estado": "error", "mensaje": "Error interno al procesar el diagnóstico."}, status=500)


@login_required(login_url='login')
def api_promedio_puntos(request):
    """
    Endpoint HTTP: GET /ia/promedio_puntos/?solicitud_id=<id>
    ---------------------------------------------------------
    Calcula los promedios estadísticos de los puntos de muestreo tomados en un terreno.

    Asegura autorización verificando que la solicitud esté asignada al laboratorista activo.
    Aplica `Avg()` de Django ORM sobre los 7 parámetros físicos y químicos.
    """
    if request.method != "GET":
        return JsonResponse({"estado": "error", "mensaje": "Solo GET permitido"}, status=405)

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
                "humedad": round(float(prom['h'] or 0.0), 1),
                "temperatura": round(float(prom['t'] or 0.0), 1),
                "conductividad": round(float(prom['c'] or 0.0), 2),
                "ph": round(float(prom['ph'] or 0.0), 1),
                "nitrogeno": round(float(prom['n'] or 0.0), 0),
                "fosforo": round(float(prom['p'] or 0.0), 0),
                "potasio": round(float(prom['k'] or 0.0), 0),
                "muestras_tomadas": puntos_tomados.count()
            }
        elif sol.modalidad == 'LLEVAR_MUESTRA':
            # Si el análisis se realiza por muestra traída al laboratorio, consulta la última lectura real del sensor
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
                return JsonResponse({
                    "estado": "error",
                    "mensaje": "No existen lecturas de sensor registradas en el laboratorio para calcular el perfil."
                }, status=400)
        else:
            return JsonResponse({
                "estado": "error",
                "mensaje": "Debes capturar al menos un punto de muestreo en el terreno antes de calcular el perfil promedio."
            }, status=400)

        return JsonResponse({"estado": "ok", "promedio": promedio_datos})
    except SolicitudAnalisis.DoesNotExist:
        return JsonResponse({"estado": "error", "mensaje": "Solicitud no encontrada o no autorizada."}, status=404)
    except Exception as e:
        logger.error("Error en api_promedio_puntos: %s", e, exc_info=True)
        return JsonResponse({"estado": "error", "mensaje": "Error interno al calcular el promedio de puntos."}, status=500)


@login_required(login_url='login')
def api_compartir_resultado(request):
    """
    Endpoint HTTP: POST /ia/compartir/
    ----------------------------------
    HU-0031: Cierre formal y entrega del análisis edafológico al agricultor.

    Operación:
      - Protegido con validación CSRF y sesión autenticada.
      - Valida que el invocador posea rol LABORATORISTA y sea el técnico asignado.
      - Valida rangos numéricos de los 7 parámetros del suelo.
      - Persiste el `RegistroAnalisis` con su dictamen completo en transacción atómica.
      - Transiciona la `SolicitudAnalisis` al estado 'COMPLETADA'.
      - Notifica disponibilidad para consulta inmediata en el historial del agricultor.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)

    if not tiene_rol(request.user, 'LABORATORISTA', 'ADMIN'):
        return JsonResponse({'error': 'No autorizado para compartir análisis'}, status=403)

    try:
        data = json.loads(request.body)
        solicitud_id = data.get("solicitud_id")
        if not solicitud_id:
            return JsonResponse({"estado": "error", "mensaje": "solicitud_id es requerido"}, status=400)

        from apps.solicitudes.models import SolicitudAnalisis

        try:
            sol = SolicitudAnalisis.objects.get(id=solicitud_id)
        except (SolicitudAnalisis.DoesNotExist, ValueError, TypeError):
            return JsonResponse({"estado": "error", "mensaje": "Solicitud no encontrada."}, status=404)

        # Control de autorización: únicamente el laboratorista a cargo puede cerrar el informe
        if sol.laboratorista_asignado != request.user and not tiene_rol(request.user, 'ADMIN'):
            registrar_evento_seguridad(
                'IDOR_BLOQUEADO_COMPARTIR',
                request=request,
                nivel='WARNING',
                detalle=f"Intento de compartir resultado de solicitud #{solicitud_id} ajena."
            )
            return JsonResponse({'error': 'No autorizado para compartir este análisis'}, status=403)

        if sol.estado not in ('ASIGNADA', 'EN_PROCESO', 'COMPLETADA'):
            return JsonResponse({
                "estado": "error",
                "mensaje": f"No se puede compartir resultados para una solicitud en estado {sol.get_estado_display()}."
            }, status=400)

        from apps.analisis.models import PuntoMuestreo
        from django.db.models import Avg

        datos = data.get("datos", {})
        if not isinstance(datos, dict):
            datos = {}

        # Autoridad en el servidor: si existen puntos de muestreo tomados en BD para esta solicitud,
        # el backend calcula el promedio real desde la base de datos en lugar de confiar en el JSON del cliente.
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
            h = round(float(prom['h'] or 0.0), 1)
            t = round(float(prom['t'] or 0.0), 1)
            c = round(float(prom['c'] or 0.0), 2)
            ph = round(float(prom['ph'] or 0.0), 1)
            n = round(float(prom['n'] or 0.0), 0)
            p = round(float(prom['p'] or 0.0), 0)
            k = round(float(prom['k'] or 0.0), 0)
        else:
            if sol.modalidad == 'VISITA' and not datos:
                return JsonResponse({
                    "estado": "error",
                    "mensaje": "No existen puntos de muestreo capturados para esta solicitud."
                }, status=400)
            h = float(datos.get('humedad', 0) or 0)
            t = float(datos.get('temperatura', 0) or 0)
            c = float(datos.get('conductividad', 0) or 0)
            ph = float(datos.get('ph', 0) or 0)
            n = float(datos.get('nitrogeno', 0) or 0)
            p = float(datos.get('fosforo', 0) or 0)
            k = float(datos.get('potasio', 0) or 0)

        es_valido_rango, msg_rango = _validar_parametros_suelo(h, t, c, ph, n, p, k)
        if not es_valido_rango:
            return JsonResponse({"estado": "error", "mensaje": msg_rango}, status=400)

        # Autoridad en el servidor sobre el diagnóstico agronómico:
        # El backend recalcula el diagnóstico determinista de referencia para asegurar que
        # los porcentajes de compatibilidad y las recomendaciones no hayan sido manipulados ni omitidos en el frontend.
        preferencia_sol = sol.cultivo_deseado or ''
        diagnostico_servidor = calcular_diagnostico_edafologico(
            h, t, c, ph, n, p, k, preferencia=preferencia_sol
        )
        diagnostico_cliente = data.get("diagnostico", {})
        if (
            isinstance(diagnostico_cliente, dict)
            and isinstance(diagnostico_cliente.get("recomendaciones"), list)
            and len(diagnostico_cliente["recomendaciones"]) > 0
        ):
            # Si viene un dictamen enriquecido (ej. Gemini AI), preservamos las explicaciones textuales pero
            # imponemos los puntajes de compatibilidad autoritativos del servidor para cultivos del catálogo.
            mapa_scores = {
                _norm(r.get("cultivo", "")): r.get("compatibilidad")
                for r in diagnostico_servidor.get("recomendaciones", [])
                if isinstance(r, dict) and r.get("cultivo")
            }
            recs_validadas = []
            for rec in diagnostico_cliente["recomendaciones"][:6]:
                if not isinstance(rec, dict) or not rec.get("cultivo"):
                    continue
                rec_copia = dict(rec)
                clave_norm = _norm(rec_copia.get("cultivo", ""))
                if clave_norm in mapa_scores:
                    rec_copia["compatibilidad"] = mapa_scores[clave_norm]
                else:
                    try:
                        comp_val = int(float(rec_copia.get("compatibilidad", 50)))
                        rec_copia["compatibilidad"] = max(5, min(99, comp_val))
                    except (ValueError, TypeError):
                        rec_copia["compatibilidad"] = 50
                recs_validadas.append(rec_copia)
            if recs_validadas:
                diagnostico = {
                    "recomendaciones": recs_validadas,
                    "consejo_general": str(
                        diagnostico_cliente.get("consejo_general")
                        or diagnostico_servidor.get("consejo_general", "")
                    )[:2000],
                    "modo": str(diagnostico_cliente.get("modo") or "ia").lower(),
                }
            else:
                diagnostico = diagnostico_servidor
        else:
            diagnostico = diagnostico_servidor

        _guardar_diagnostico_solicitud(
            solicitud_id,
            diagnostico,
            h, t, c, ph, n, p, k,
        )

        registrar_evento_seguridad(
            'ANALISIS_COMPARTIDO',
            request=request,
            detalle=f"Solicitud #{solicitud_id} completada y compartida con agricultor id={sol.agricultor_id}."
        )

        nombre_agri = sol.agricultor.get_full_name() or sol.agricultor.username
        return JsonResponse({
            "estado": "ok",
            "mensaje": f"Resultados compartidos exitosamente con {nombre_agri}. El informe ya está disponible en su historial."
        })
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"estado": "error", "mensaje": "Datos de entrada inválidos."}, status=400)
    except Exception as e:
        logger.error("Error en api_compartir_resultado: %s", e, exc_info=True)
        return JsonResponse({"estado": "error", "mensaje": "Error interno al compartir los resultados."}, status=500)


@login_required(login_url='login')
def api_sincronizar_offline(request):
    """
    Endpoint HTTP: POST /ia/sincronizar-offline/
    -------------------------------------------
    HU-0032: Sincronización masiva por lotes de muestreos y análisis recopilados sin conexión.

    Controles de Seguridad:
      - Exige sesión autenticada, token CSRF válido y rol 'LABORATORISTA' o 'ADMIN'.
      - Verifica propiedad estricta (`sol.laboratorista_asignado == request.user`) por cada
        solicitud del lote para impedir ataques IDOR/BOLA sobre órdenes de otros técnicos.
      - Limita el lote a un máximo de 50 elementos por petición.
      - Ejecuta las actualizaciones dentro de una transacción atómica por solicitud.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)

    if not tiene_rol(request.user, 'LABORATORISTA', 'ADMIN'):
        registrar_evento_seguridad(
            'SYNC_OFFLINE_NO_AUTORIZADO',
            request=request,
            nivel='WARNING',
            detalle='Intento de sincronización offline sin rol LABORATORISTA/ADMIN.'
        )
        return JsonResponse({"error": "No autorizado"}, status=403)

    if not verificar_rate_limit(request, 'ia_sync_offline', max_requests=20, window_seconds=60):
        return JsonResponse({"estado": "error", "mensaje": "Demasiadas solicitudes de sincronización. Intenta en un minuto."}, status=429)

    try:
        data = json.loads(request.body)
        items = data.get("items", [])
        if not isinstance(items, list) or not items:
            return JsonResponse({"estado": "ok", "sincronizados": 0, "mensaje": "No hay elementos para sincronizar"})

        from apps.solicitudes.models import SolicitudAnalisis
        from apps.analisis.models import PuntoMuestreo

        sincronizados = 0
        es_admin = tiene_rol(request.user, 'ADMIN')

        for item in items[:50]:
            if not isinstance(item, dict):
                continue
            sol_id = item.get("solicitud_id")
            datos = item.get("datos", {}) if isinstance(item.get("datos"), dict) else {}
            diagnostico = item.get("diagnostico", {})
            puntos = item.get("puntos", []) if isinstance(item.get("puntos"), list) else []

            if sol_id:
                try:
                    sol = SolicitudAnalisis.objects.get(id=sol_id)
                    # Verificación anti-IDOR: el laboratorista solo puede sincronizar sus propias solicitudes asignadas
                    if not es_admin and sol.laboratorista_asignado_id != request.user.id:
                        registrar_evento_seguridad(
                            'IDOR_BLOQUEADO_SYNC_OFFLINE',
                            request=request,
                            nivel='WARNING',
                            detalle=f"Intento de sincronizar solicitud #{sol_id} no asignada al usuario."
                        )
                        continue

                    if sol.estado not in ('ASIGNADA', 'EN_PROCESO', 'COMPLETADA'):
                        continue

                    h = float(datos.get('humedad', 0) or 0)
                    t = float(datos.get('temperatura', 0) or 0)
                    c = float(datos.get('conductividad', 0) or 0)
                    ph = float(datos.get('ph', 0) or 0)
                    n = float(datos.get('nitrogeno', 0) or 0)
                    p = float(datos.get('fosforo', 0) or 0)
                    k = float(datos.get('potasio', 0) or 0)

                    es_valido_rango, _ = _validar_parametros_suelo(h, t, c, ph, n, p, k)
                    if not es_valido_rango:
                        continue

                    with transaction.atomic():
                        from django.db.models import Avg
                        # 1. Validar y persistir primero los puntos individuales georreferenciados (máx 25 puntos por lote)
                        for p_data in puntos[:25]:
                            if not isinstance(p_data, dict):
                                continue
                            p_num = p_data.get("numero")
                            if p_num and isinstance(p_num, int) and 1 <= p_num <= 50:
                                ph_p = float(p_data.get("ph", ph) or ph)
                                h_p = float(p_data.get("humedad", h) or h)
                                t_p = float(p_data.get("temperatura", t) or t)
                                c_p = float(p_data.get("conductividad", c) or c)
                                n_p = float(p_data.get("nitrogeno", n) or n)
                                p_p = float(p_data.get("fosforo", p) or p)
                                k_p = float(p_data.get("potasio", k) or k)
                                ok_p, _ = _validar_parametros_suelo(h_p, t_p, c_p, ph_p, n_p, p_p, k_p)
                                if not ok_p:
                                    continue
                                punto, _ = PuntoMuestreo.objects.get_or_create(solicitud=sol, numero=p_num)
                                punto.humedad = h_p
                                punto.temperatura = t_p
                                punto.conductividad = c_p
                                punto.ph = ph_p
                                punto.nitrogeno = n_p
                                punto.fosforo = p_p
                                punto.potasio = k_p
                                if p_data.get("latitud") is not None:
                                    lat = float(p_data.get("latitud"))
                                    if -90.0 <= lat <= 90.0:
                                        punto.latitud = lat
                                if p_data.get("longitud") is not None:
                                    lon = float(p_data.get("longitud"))
                                    if -180.0 <= lon <= 180.0:
                                        punto.longitud = lon
                                if p_data.get("altitud") is not None:
                                    alt = float(p_data.get("altitud"))
                                    if -500.0 <= alt <= 9000.0:
                                        punto.altitud = alt
                                punto.estado = 'TOMADO'
                                punto.save()

                        # 2. Si existen puntos tomados para la solicitud, recalcular el promedio en el servidor
                        puntos_tomados_sync = PuntoMuestreo.objects.filter(solicitud=sol, estado='TOMADO')
                        if puntos_tomados_sync.exists():
                            prom_sync = puntos_tomados_sync.aggregate(
                                h=Avg('humedad'),
                                t=Avg('temperatura'),
                                c=Avg('conductividad'),
                                ph=Avg('ph'),
                                n=Avg('nitrogeno'),
                                p=Avg('fosforo'),
                                k=Avg('potasio')
                            )
                            h = round(float(prom_sync['h'] or h), 1)
                            t = round(float(prom_sync['t'] or t), 1)
                            c = round(float(prom_sync['c'] or c), 2)
                            ph = round(float(prom_sync['ph'] or ph), 1)
                            n = round(float(prom_sync['n'] or n), 0)
                            p = round(float(prom_sync['p'] or p), 0)
                            k = round(float(prom_sync['k'] or k), 0)

                        # 3. Recalcular el diagnóstico agronómico en el backend para no depender del cálculo JS en caché
                        diagnostico_autorizado = calcular_diagnostico_edafologico(
                            h, t, c, ph, n, p, k, preferencia=sol.cultivo_deseado or ''
                        )

                        # 4. Persistencia consolidada autoritativa
                        _guardar_diagnostico_solicitud(
                            sol_id,
                            diagnostico_autorizado,
                            h, t, c, ph, n, p, k,
                        )

                    sincronizados += 1
                except (SolicitudAnalisis.DoesNotExist, ValueError, TypeError):
                    continue

        if sincronizados > 0:
            registrar_evento_seguridad(
                'SINCRONIZACION_OFFLINE_EXITOSA',
                request=request,
                detalle=f"Sincronizados {sincronizados} análisis offline."
            )

        return JsonResponse({
            "estado": "ok",
            "sincronizados": sincronizados,
            "mensaje": f"Se han sincronizado {sincronizados} análisis guardados localmente."
        })
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"estado": "error", "mensaje": "Payload JSON de sincronización inválido."}, status=400)
    except Exception as e:
        logger.error("Error en api_sincronizar_offline: %s", e, exc_info=True)
        return JsonResponse({"estado": "error", "mensaje": "Error interno durante la sincronización offline."}, status=500)


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
    Cálculo matemático canónico del porcentaje de compatibilidad de un cultivo,
    calibrado para sondas RS485 Modbus 7 en 1.

    Separa la aptitud edafoclimática estructural (pH 30%, Temp 15%, Humedad 15%) de la
    concentración soluble de nutrientes (N 10%, P 10%, K 10%, CE 10%). Homologa la
    conductividad eléctrica a dS/m y aplica la curva de suficiencia para iones libres in-situ.

    Retorna:
        tuple: (porcentaje_entero_0_a_100 | None, lista_de_diagnósticos_por_variable)
    """
    total, peso, detalle = 0.0, 0.0, []

    # 1. pH (30%)
    ph_v = float(ph or 0)
    if ph_v > 0:
        ph_lo, ph_hi = float(cultivo.ph_min), float(cultivo.ph_max)
        if ph_lo <= ph_v <= ph_hi:
            score_ph = 100.0
            estado = "dentro del rango ideal"
        elif ph_v < ph_lo:
            diff = ph_lo - ph_v
            score_ph = max(10.0, 100.0 - (diff / 1.5) * 75.0)
            estado = "ácido para el cultivo (requiere encalado)"
        else:
            diff = ph_v - ph_hi
            score_ph = max(10.0, 100.0 - (diff / 1.5) * 75.0)
            estado = "alcalino para el cultivo (requiere materia orgánica)"
        total += score_ph * 0.30
        peso += 0.30
        detalle.append(f"pH: {ph_v:g} (ideal {ph_lo:g} - {ph_hi:g}) -> {estado}")

    # 2. Humedad (15%)
    h_v = float(h or 0)
    if h_v > 0:
        h_lo, h_hi = float(cultivo.humedad_min), float(cultivo.humedad_max)
        if h_lo <= h_v <= h_hi:
            score_h = 100.0
            estado = "óptima (capacidad de campo)"
        elif h_v < h_lo:
            score_h = max(35.0, (h_v / max(h_lo, 1.0)) * 90.0)
            estado = "por debajo del óptimo (requiere riego)"
        else:
            score_h = max(30.0, 100.0 - ((h_v - h_hi) / max(h_hi, 1.0)) * 50.0)
            estado = "alta humedad (verificar drenajes)"
        total += score_h * 0.15
        peso += 0.15
        detalle.append(f"Humedad: {h_v:g}% (ideal {h_lo:g} - {h_hi:g}%) -> {estado}")

    # 3. Temperatura (15%)
    t_v = float(t or 0)
    if t_v > 0:
        t_lo, t_hi = float(cultivo.temperatura_min), float(cultivo.temperatura_max)
        if t_lo <= t_v <= t_hi:
            score_t = 100.0
            estado = "en rango térmico óptimo"
        else:
            diff_t = (t_lo - t_v) if t_v < t_lo else (t_v - t_hi)
            score_t = max(25.0, 100.0 - (diff_t / 8.0) * 70.0)
            estado = "fuera del rango térmico óptimo"
        total += score_t * 0.15
        peso += 0.15
        detalle.append(f"Temperatura: {t_v:g} °C (ideal {t_lo:g} - {t_hi:g} °C) -> {estado}")

    # 4. Nitrógeno N (10%)
    n_v = float(n or 0)
    if n_v > 0:
        n_lo, n_hi = float(cultivo.nitrogeno_min), float(cultivo.nitrogeno_max)
        score_n = _evaluar_npk_sonda_7en1(n_v, n_lo, n_hi, h_v, tipo='n')
        total += score_n * 0.10
        peso += 0.10
        estado_n = "en rango óptimo" if n_v >= n_lo else (
            "reserva soluble moderada en sonda (acompañar con abono orgánico/químico)" if score_n >= 80 else
            "bajo en solución (plan de fertilización nitrogenada requerido)"
        )
        detalle.append(f"Nitrógeno (sonda): {n_v:g} mg/kg (ref. lab {n_lo:g} - {n_hi:g} mg/kg) -> {estado_n}")

    # 5. Fósforo P (10%)
    p_v = float(p or 0)
    if p_v > 0:
        p_lo, p_hi = float(cultivo.fosforo_min), float(cultivo.fosforo_max)
        score_p = _evaluar_npk_sonda_7en1(p_v, p_lo, p_hi, h_v, tipo='p')
        total += score_p * 0.10
        peso += 0.10
        estado_p = "en rango óptimo" if p_v >= p_lo else (
            "reserva soluble adecuada en sonda (fijación coloidal normal en suelo)" if score_p >= 80 else
            "bajo en solución (reforzar con fósforo radicular)"
        )
        detalle.append(f"Fósforo (sonda): {p_v:g} mg/kg (ref. lab {p_lo:g} - {p_hi:g} mg/kg) -> {estado_p}")

    # 6. Potasio K (10%)
    k_v = float(k or 0)
    if k_v > 0:
        k_lo, k_hi = float(cultivo.potasio_min), float(cultivo.potasio_max)
        score_k = _evaluar_npk_sonda_7en1(k_v, k_lo, k_hi, h_v, tipo='k')
        total += score_k * 0.10
        peso += 0.10
        estado_k = "en rango óptimo" if k_v >= k_lo else (
            "reserva soluble moderada en sonda (incorporar potasio en llenado)" if score_k >= 80 else
            "bajo en solución (plan de fertilización potásica requerido)"
        )
        detalle.append(f"Potasio (sonda): {k_v:g} mg/kg (ref. lab {k_lo:g} - {k_hi:g} mg/kg) -> {estado_k}")

    # 7. Conductividad Eléctrica CE (10%)
    c_v = float(c or 0)
    if c_v > 0:
        c_lo, c_hi = float(cultivo.conductividad_min), float(cultivo.conductividad_max)
        score_c, c_dsm = _evaluar_ce_sonda_7en1(c_v, c_lo, c_hi)
        total += score_c * 0.10
        peso += 0.10
        estado_c = "salinidad balanceada" if c_lo <= c_dsm <= c_hi else (
            "baja salinidad (suelo natural seguro para raíces/plántulas)" if c_dsm < c_lo else
            "salinidad alta (precaución osmótica)"
        )
        detalle.append(f"Conductividad: {c_v:g} µS/cm ({c_dsm:.2f} dS/m, ideal {c_lo:g} - {c_hi:g} dS/m) -> {estado_c}")

    if peso == 0:
        return None, detalle

    return int(round(total / peso)), detalle


@login_required(login_url='login')
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

    if not verificar_rate_limit(request, 'ia_consulta_cultivo', max_requests=30, window_seconds=60):
        return JsonResponse({"estado": "error", "mensaje": "Demasiadas consultas seguidas. Por favor espera un minuto."}, status=429)

    try:
        data = json.loads(request.body)
        solicitud_id = data.get("solicitud_id")
        cultivo_busqueda = str(data.get("cultivo", "")).strip()[:100]

        if not solicitud_id or not cultivo_busqueda:
            return JsonResponse({"estado": "error", "mensaje": "Faltan datos de consulta"}, status=400)

        from apps.analisis.models import RegistroAnalisis

        # Validación de seguridad: el análisis debe pertenecer al agricultor, al laboratorista asignado o ser consultado por ADMIN
        try:
            if tiene_rol(request.user, 'ADMIN'):
                analisis = RegistroAnalisis.objects.get(solicitud_id=solicitud_id)
            else:
                analisis = RegistroAnalisis.objects.get(
                    Q(solicitud__agricultor=request.user) |
                    Q(solicitud__laboratorista_asignado=request.user),
                    solicitud_id=solicitud_id,
                )
        except (RegistroAnalisis.DoesNotExist, ValueError, TypeError):
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
                    "\nNota técnica de la sonda in-situ: Las lecturas provienen de una sonda RS485 7 en 1 que mide la solución iónica del suelo. "
                    "En suelos donde crecen plántulas o plantas vivas, es normal registrar NPK soluble moderado sin fertilizante sintético reciente. "
                    "Explica la aptitud con enfoque constructivo y enfoca la recomendación en el plan de fertilización y abonado.\n"
                    "Responde SOLO con JSON válido (sin markdown) con estas dos claves:\n"
                    '{"descripcion": "explicación clara de por qué este suelo sirve para el cultivo y su potencial agronómico", '
                    '"recomendacion_suelo": "plan de fertilización o enmiendas concretas para nutrir adecuadamente el cultivo"}'
                )
                res = model.generate_content(prompt)
                raw = res.text.strip()
                ini, fin = raw.find('{'), raw.rfind('}')
                texto = json.loads(raw[ini:fin + 1] if ini != -1 and fin != -1 else raw)
            except Exception as ex:
                logger.warning("Fallo Gemini en api_consultar_ia_agricultor: %s", ex)
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
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"estado": "error", "mensaje": "Formato de consulta inválido."}, status=400)
    except Exception as e:
        logger.error("Error en api_consultar_ia_agricultor: %s", e, exc_info=True)
        return JsonResponse({"estado": "error", "mensaje": "Error interno al procesar la consulta."}, status=500)


# ==============================================================================
# ASESOR AGRONÓMICO Y EDAFOLÓGICO CONVERSACIONAL (GUARDRAIL ESTRICTO AGRÍCOLA)
# ==============================================================================

PALABRAS_FUERA_DE_DOMINIO = {
    'futbol', 'partido', 'mundial', 'messi', 'cristiano', 'gol', 'champions',
    'pelicula', 'netflix', 'cine', 'actor', 'cancion', 'musica', 'reggaeton',
    'videojuego', 'fortnite', 'minecraft', 'gta', 'playstation', 'xbox',
    'programar', 'javascript', 'python', 'html', 'css', 'django', 'codigo fuente',
    'criptomoneda', 'bitcoin', 'trading', 'bolsa de valores', 'apuesta', 'casino',
    'horoscopo', 'tarot', 'astrologia', 'chiste', 'broma', 'adivinanza',
    'presidente', 'elecciones', 'politica', 'congreso', 'famosos', 'farandula',
    'pizza', 'hamburguesa', 'receta de cocina', 'postre', 'pasteleria',
}

PALABRAS_DOMINIO_AGRICOLA = {
    'suelo', 'tierra', 'terreno', 'lote', 'finca', 'parcela', 'maceta', 'jardin',
    'huerta', 'huerto', 'campo', 'sembrar', 'plantar', 'cultivar', 'cultivo',
    'planta', 'arbol', 'brote', 'semilla', 'raiz', 'raices', 'hoja', 'tallo',
    'flor', 'fruto', 'cosecha', 'botanica', 'agronomia', 'agricola', 'agricultura',
    'agricultor', 'campesino', 'abono', 'abonar', 'fertilizante', 'fertilizar',
    'fertilizacion', 'enmienda', 'compost', 'compostaje', 'humus', 'lombriz',
    'materia organica', 'cal', 'dolomita', 'encalar', 'encalado', 'urea', 'dap',
    'npk', 'nitrogeno', 'fosforo', 'potasio', 'nutriente', 'nutrientes',
    'macronutriente', 'micronutriente', 'ph', 'acidez', 'acido', 'alcalino',
    'salinidad', 'conductividad', 'humedad', 'agua', 'riego', 'regar', 'drenaje',
    'encharcamiento', 'seco', 'seca', 'temperatura', 'clima', 'sol', 'sombra',
    'sombrio', 'sonda', 'sensor', 'esp32', 'lectura', 'analisis', 'muestra',
    'diagnostico', 'plaga', 'hongo', 'maleza', 'poda', 'podar', 'germinar',
    'germinacion', 'vivero', 'sustrato', 'arena', 'arcilla', 'limo', 'franco',
    'erosion', 'arar', 'labranza', 'cafe', 'cacao', 'maiz', 'arroz', 'platano',
    'aguacate', 'tomate', 'frijol', 'yuca', 'papa', 'citrico', 'limon', 'naranja',
    'fruta', 'hortaliza', 'leguminosa', 'pasto', 'forraje', 'iniciar', 'mejorar',
    'recuperar', 'preparar', 'corregir', 'ion', 'iones', 'mineral', 'minerales',
}


def _es_consulta_agricola_valida(pregunta):
    """
    Verifica si la consulta del usuario pertenece al dominio agronómico,
    edafológico, botánico o de interpretación del análisis de suelo.
    """
    texto_norm = _norm(pregunta)
    if not texto_norm or len(texto_norm) < 3:
        return False

    # Si contiene términos explícitamente ajenos al agro y ningún término agrícola fuerte
    for palabra_prohibida in PALABRAS_FUERA_DE_DOMINIO:
        if palabra_prohibida in texto_norm:
            tiene_contexto_agro = any(p in texto_norm for p in ('suelo', 'tierra', 'cultivo', 'planta', 'sembrar', 'abono', 'ph', 'npk'))
            if not tiene_contexto_agro:
                return False

    # Comprobar presencia de al menos un concepto vinculado al agro, suelo, plantas o análisis
    for palabra_agro in PALABRAS_DOMINIO_AGRICOLA:
        if palabra_agro in texto_norm:
            return True

    return False


def _generar_asesoria_offline(pregunta, h, t, c, ph, n, p, k, nombre_terreno):
    """
    Motor experto local para responder dudas sobre suelos, botánica, inicio de siembra
    y funcionamiento del análisis cuando no hay conexión a internet.
    """
    q = _norm(pregunta)
    pasos = []

    # Evaluación del estado actual de la muestra para personalizar el consejo
    diagnostico_suelo = []
    if ph > 0:
        if ph < 5.5:
            diagnostico_suelo.append(f"pH ácido ({ph}): aplicar cal dolomita o agrícola (150-250 g/m² o 1.5-2.5 t/ha) antes de abonar")
        elif ph > 7.3:
            diagnostico_suelo.append(f"pH alcalino ({ph}): incorporar compost maduro o azufre elemental para mejorar la disponibilidad de micronutrientes")
        else:
            diagnostico_suelo.append(f"pH balanceado ({ph}): rango ideal para la asimilación de nutrientes")

    if n < 50 or p < 20 or k < 80:
        diagnostico_suelo.append(f"Nutrientes NPK bajos (N:{n:g}, P:{p:g}, K:{k:g} mg/kg): el suelo requiere enriquecimiento con humus de lombriz o fertilizante compuesto NPK")
    else:
        diagnostico_suelo.append(f"Reserva NPK activa (N:{n:g}, P:{p:g}, K:{k:g} mg/kg): buena base nutricional para el desarrollo vegetativo")

    if h > 0 and h < 35:
        diagnostico_suelo.append(f"Humedad baja ({h}%): regar hasta capacidad de campo (50%-65%) para activar la solución del suelo")
    elif h > 80:
        diagnostico_suelo.append(f"Humedad alta ({h}%): mejorar el drenaje para evitar asfixia radicular")

    resumen_muestra = "; ".join(diagnostico_suelo) if diagnostico_suelo else "Parámetros listos para evaluación agronómica."

    # Caso 1: Dudas sobre conductividad, humedad, sensor o por qué salen datos bajos
    if any(w in q for w in ('conductividad', 'sensor', 'sonda', 'por que', 'bajo', 'cero', 'funciona', 'analisis', 'lectura', 'ion')):
        titulo = "Explicación Técnica del Análisis de Suelo y Sonda Edafológica"
        respuesta = (
            f"En el lote '{nombre_terreno}', los resultados reflejan la física y química real de la solución del suelo. "
            "Los macronutrientes Nitrógeno, Fósforo y Potasio (NPK) existen en forma de iones minerales disueltos. "
            "Si la tierra está seca o tiene baja humedad, los iones permanecen cristalizados en estado sólido y no conducen electricidad, "
            "haciendo que la conductividad eléctrica y las lecturas de NPK marquen valores bajos o cercanos a cero. "
            "Además, una planta ya establecida puede verse viva porque consume reservas acumuladas en sus tejidos, aunque el suelo ya esté agotado."
        )
        pasos = [
            "Humedecer la muestra de suelo con agua limpia hasta alcanzar un 50% - 60% de humedad (capacidad de campo, húmeda pero sin escurrir).",
            "Esperar entre 5 y 10 minutos antes de medir para permitir que el agua disuelva las sales minerales y libere los iones NPK.",
            "Compactar ligeramente la tierra alrededor de las varillas de acero de la sonda para eliminar bolsas de aire.",
            "Verificar que la sonda reciba su alimentación estable de 12V DC para polarizar correctamente los electrodos."
        ]

    # Caso 2: Cómo iniciar desde cero en jardín, huerta, botánica o campo
    elif any(w in q for w in ('iniciar', 'empezar', 'comenzar', 'jardin', 'huerta', 'huerto', 'botanica', 'primera vez', 'principiante', 'maceta')):
        titulo = "Guía Paso a Paso para Iniciar tu Proyecto Botánico o Agrícola"
        respuesta = (
            f"Para iniciar con éxito en '{nombre_terreno}' (ya sea en jardín, huerta casera o lote de campo), el secreto agronómico "
            "es preparar primero la 'casa de las raíces' antes de poner la semilla o plántula. Un suelo suelto, aireado, con buen drenaje "
            "y rico en materia orgánica garantiza que cualquier planta prenda vigorosamente desde la primera semana."
        )
        pasos = [
            "Preparación física (Descompactación): Afloja la tierra a una profundidad de 20 a 30 cm retirando piedras, terrones duros y restos de raíces viejas.",
            "Acondicionamiento orgánico: Mezcla un 30% de abono orgánico estabilizado (humus de lombriz o compost maduro) con el 70% de tu tierra para mejorar textura y retención de agua.",
            f"Corrección química según tu muestra (pH {ph}): " + ("Aplica una cucharada de cal dolomita por litro de sustrato (o 200 g/m²) para suavizar la acidez." if ph < 5.5 else "Tu pH actual permite sembrar directamente sin necesidad de encalar."),
            "Riego de asiento y siembra: Humedece el sustrato un día antes de sembrar, ubica la planta sin enterrar el cuello del tallo y mantén sombra parcial los primeros 8 días."
        ]

    # Caso 3: Cómo mejorar o recuperar el suelo
    else:
        titulo = "Plan Integral de Mejoramiento y Recuperación de Suelo"
        respuesta = (
            f"Analizando las condiciones actuales de '{nombre_terreno}' (pH {ph}, Humedad {h}%, CE {c} µS/cm, "
            f"N:{n:g} - P:{p:g} - K:{k:g} mg/kg), el mejoramiento del suelo debe enfocarse en activar la microbiología edáfica, "
            "equilibrar la acidez y restituir los macronutrientes esenciales para que las raíces puedan absorberlos sin bloqueos químicos."
        )
        pasos = [
            "Incorporación de Materia Orgánica: Aplica de 2 a 4 kg/m² de compost o lombricompost para aumentar la Capacidad de Intercambio Catiónico (CIC) y esponjosidad del suelo.",
            "Regulación de pH y Calcio: " + ("Dado el pH ácido de la muestra, incorpora cal agrícola o dolomita al menos 15 días antes de aplicar fertilizantes granulados." if ph < 5.5 else "Mantén el pH estable mediante aportes periódicos de materia orgánica humificada."),
            "Nutrición Balanceada NPK: Refuerza con fuentes ricas en Fósforo (DAP o roca fosfórica) para estimular raíces, Nitrógeno fraccionado para follaje y Potasio para resistencia hídrica.",
            "Cobertura vegetal (Mulching): Cubre la superficie del suelo con hojarasca seca o restos vegetales para conservar la humedad entre 50%-65% y evitar el recalentamiento radicular."
        ]

    return {
        "es_valido": True,
        "titulo": titulo,
        "respuesta_principal": respuesta,
        "pasos_recomendados": pasos,
        "consejo_suelo": resumen_muestra
    }


@login_required(login_url='login')
def api_asesor_agronomico(request):
    """
    Endpoint HTTP: POST /api/ia/asesor-suelo/
    -----------------------------------------
    Asistente abierto para el laboratorista/agricultor en el Historial de Análisis.
    Resuelve dudas sobre:
      - Cómo mejorar o recuperar el suelo analizado.
      - Cómo iniciar un proyecto botánico, jardín, huerta o cultivo en campo.
      - Dudas técnicas sobre el análisis de suelo (conductividad, humedad, NPK, pH, sensores).
    Aplica un filtro estricto (Guardrail) que rechaza cualquier pregunta ajena a la agricultura y suelos.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)

    if not verificar_rate_limit(request, 'ia_asesor_suelo', max_requests=25, window_seconds=60):
        return JsonResponse({"estado": "error", "mensaje": "Demasiadas consultas seguidas. Por favor espera un minuto."}, status=429)

    try:
        data = json.loads(request.body)
        pregunta = str(data.get("pregunta") or "").strip()[:600]
        solicitud_id = data.get("solicitud_id")
        datos_muestra = data.get("datos_muestra") if isinstance(data.get("datos_muestra"), dict) else {}

        if not pregunta:
            return JsonResponse({"estado": "error", "mensaje": "Por favor escribe tu consulta agrícola o sobre el suelo."}, status=400)

        # 1. Extraer parámetros de la muestra (desde BD con control anti-IDOR o desde el payload del modal)
        h = float(datos_muestra.get("humedad", 0) or 0)
        t = float(datos_muestra.get("temperatura", 0) or 0)
        c = float(datos_muestra.get("conductividad", 0) or 0)
        ph = float(datos_muestra.get("ph", 0) or 0)
        n = float(datos_muestra.get("n", 0) or 0)
        p = float(datos_muestra.get("p", 0) or 0)
        k = float(datos_muestra.get("k", 0) or 0)
        nombre_terreno = str(datos_muestra.get("terreno") or "Lote Analizado")[:100]

        if solicitud_id:
            from apps.analisis.models import RegistroAnalisis
            qs_reg = RegistroAnalisis.objects.filter(solicitud_id=solicitud_id).select_related('solicitud__terreno')
            if not tiene_rol(request.user, 'ADMIN'):
                qs_reg = qs_reg.filter(
                    Q(solicitud__agricultor=request.user) |
                    Q(solicitud__laboratorista_asignado=request.user)
                )
            reg = qs_reg.first()
            if not reg:
                registrar_evento_seguridad(
                    'IDOR_BLOQUEADO_ASESOR',
                    request=request,
                    nivel='WARNING',
                    detalle=f"Intento de consultar asesor sobre solicitud #{solicitud_id} no autorizada."
                )
                return JsonResponse({"estado": "error", "mensaje": "Análisis no encontrado o no autorizado."}, status=404)

            h = float(reg.humedad or h)
            t = float(reg.temperatura or t)
            c = float(reg.conductividad or c)
            ph = float(reg.ph or ph)
            n = float(reg.nitrogeno or n)
            p = float(reg.fosforo or p)
            k = float(reg.potasio or k)
            if reg.solicitud and reg.solicitud.terreno:
                nombre_terreno = reg.solicitud.terreno.nombre

        # 2. Intentar consulta con Google Gemini (con Guardrail estricto en el prompt)
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai is not None and verificar_conexion_internet(timeout=1.5):
            genai.configure(api_key=api_key)
            prompt = f"""
Eres el Ingeniero Agrónomo, Edafólogo y Botánico Experto de la plataforma TierSystem en el Huila, Colombia.
Un usuario está revisando el análisis de suelo del terreno '{nombre_terreno}' con las siguientes lecturas reales del sensor:
- Humedad: {h}%
- Temperatura: {t}°C
- Conductividad Eléctrica: {c} µS/cm
- pH del Suelo: {ph}
- Nitrógeno (N): {n} mg/kg
- Fósforo (P): {p} mg/kg
- Potasio (K): {k} mg/kg

El usuario realiza la siguiente consulta o petición:
"{pregunta}"

REGLA DE ORO ESTRICTA (GUARDRAIL DE DOMINIO):
- SOLO puedes responder preguntas relacionadas con: agricultura, agronomía, suelos, tierra, abonos, fertilizantes, enmiendas, botánica, jardinería, huertas, cómo sembrar o iniciar un cultivo/planta, riego, drenaje, plagas agrícolas, o dudas técnicas sobre cómo funciona el análisis de suelo y sus parámetros (pH, NPK, conductividad eléctrica, humedad, temperatura, sondas de suelo).
- IMPORTANTE SOBRE EL SENSOR 7 EN 1: La sonda de suelo mide la conductividad eléctrica de la solución acuosa en el poro del suelo. En suelos agrícolas con plantas o plántulas en crecimiento (como café), las lecturas de NPK solubles suelen ser moderadas o bajas (15 a 60 mg/kg) si no se aplicó fertilizante mineral recientemente. Explica al usuario que una planta viva demuestra fertilidad biológica y reserva orgánica en el suelo, y que las lecturas de la sonda indican la disponibilidad iónica inmediata, guiando la necesidad de riego a capacidad de campo (50-65%) y fertilización de sostenimiento, no la infertilidad del suelo.
- Si la pregunta del usuario trata sobre CUALQUIER OTRO TEMA ajeno a suelos, plantas o agricultura (por ejemplo: deportes, fútbol, política, programación, matemáticas generales, recetas de cocina, chistes, películas, videojuegos, historia general, etc.), DEBES rechazarla amablemente devolviendo `"es_valido": false`.

Devuelve ESTRICTAMENTE un objeto JSON válido (sin bloques markdown ```json) con esta estructura exacta:
{{
  "es_valido": true,
  "titulo": "Título claro y amigable de la respuesta",
  "respuesta_principal": "Explicación clara, empática, pedagógica y completa a la duda del usuario, integrando los valores actuales de su suelo si aplica.",
  "pasos_recomendados": [
    "Paso 1 práctico y detallado...",
    "Paso 2 práctico y detallado...",
    "Paso 3 práctico y detallado..."
  ],
  "consejo_suelo": "Diagnóstico breve sobre qué hacer con los valores actuales de pH ({ph}), humedad ({h}%), conductividad ({c} µS/cm) y NPK ({n}-{p}-{k} mg/kg) de esta muestra."
}}

Si la pregunta NO es de agricultura, suelos, botánica o análisis edafológico, devuelve:
{{
  "es_valido": false,
  "titulo": "Consulta Fuera del Ámbito Agrícola y de Suelos",
  "respuesta_principal": "Lo siento, soy el Asistente Especializado en Suelos y Agricultura de TierSystem. Solo estoy autorizado para resolver dudas sobre manejo y mejora de suelos, interpretación de análisis edafológicos (NPK, pH, humedad, conductividad), botánica, jardinería y cultivos. Por favor, realiza una pregunta relacionada con el campo o tu suelo.",
  "pasos_recomendados": [],
  "consejo_suelo": ""
}}
"""
            for nombre_modelo in ['gemini-flash-lite-latest', 'gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.0-flash']:
                try:
                    model = genai.GenerativeModel(nombre_modelo)
                    res = model.generate_content(prompt, request_options={"timeout": 12.0})
                    raw = res.text.replace("```json", "").replace("```", "").strip()
                    ini, fin = raw.find('{'), raw.rfind('}')
                    json_str = raw[ini:fin + 1] if (ini != -1 and fin != -1) else raw
                    asesoria = json.loads(json_str)

                    return JsonResponse({
                        "estado": "ok",
                        "asesoria": asesoria,
                        "modo": "online",
                        "modelo": nombre_modelo
                    })
                except Exception as ex:
                    logger.warning("Fallo Gemini en api_asesor_agronomico (%s): %s", nombre_modelo, ex)
                    continue

        # 3. Fallback determinista Offline con validación estricta de dominio agrícola
        if not _es_consulta_agricola_valida(pregunta):
            return JsonResponse({
                "estado": "ok",
                "asesoria": {
                    "es_valido": False,
                    "titulo": "Consulta Fuera del Ámbito Agrícola y de Suelos",
                    "respuesta_principal": "Lo siento, soy el Asistente Especializado en Suelos y Agricultura de TierSystem. Solo estoy autorizado para responder dudas sobre mejoramiento de tierras, interpretación de análisis fisicoquímicos (pH, NPK, humedad, conductividad), botánica, jardinería y manejo de cultivos. Por favor, formula una pregunta sobre suelos o agricultura.",
                    "pasos_recomendados": [],
                    "consejo_suelo": ""
                },
                "modo": "offline"
            })

        asesoria_offline = _generar_asesoria_offline(pregunta, h, t, c, ph, n, p, k, nombre_terreno)
        return JsonResponse({
            "estado": "ok",
            "asesoria": asesoria_offline,
            "modo": "offline"
        })

    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"estado": "error", "mensaje": "Datos de consulta inválidos."}, status=400)
    except Exception as e:
        logger.error("Error en api_asesor_agronomico: %s", e, exc_info=True)
        return JsonResponse({"estado": "error", "mensaje": "Error interno al procesar la consulta agrícola."}, status=500)
