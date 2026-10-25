import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from apps.cultivos.models import Cultivo

# Intentar importar google.generativeai, manejando si aún no está instalado
try:
    import google.generativeai as genai
except ImportError:
    genai = None

def _guardar_recomendaciones_relacionales(registro, diagnostico):
    """Guarda cada recomendación en la tabla relacional RecomendacionAnalisis en MySQL."""
    if not diagnostico or not isinstance(diagnostico, dict):
        return
    from apps.analisis.models import RecomendacionAnalisis
    from apps.cultivos.models import Cultivo
    
    # Limpiar recomendaciones anteriores del mismo registro para evitar duplicados
    registro.recomendaciones.all().delete()
    
    recs = diagnostico.get("recomendaciones", [])
    for rec in recs:
        nombre = rec.get("cultivo", "Cultivo")
        nombre_limpio = nombre.split('(')[0].strip()
        compat = float(rec.get("compatibilidad", 0.0))
        desc = rec.get("descripcion", "")
        plan = rec.get("plan_fertilizacion", "")
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
    """Helper que centraliza el guardado de RegistroAnalisis y sus recomendaciones relacionales."""
    if not solicitud_id:
        return None
    from apps.solicitudes.models import SolicitudAnalisis
    from apps.analisis.models import RegistroAnalisis
    try:
        sol = SolicitudAnalisis.objects.get(id=solicitud_id)
    except SolicitudAnalisis.DoesNotExist:
        return None
        
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
    sol.estado = 'COMPLETADA'
    sol.save()
    
    # Guardado relacional en base de datos
    _guardar_recomendaciones_relacionales(registro, diagnostico)
    return registro


def obtener_modelo_gemini():
    """Retorna un modelo Gemini activo con fallback a gemini-1.5-flash."""
    for nombre in ['gemini-flash-lite-latest', 'gemini-flash-latest']:
        try:
            return genai.GenerativeModel(nombre)
        except Exception:
            continue
    return genai.GenerativeModel('gemini-flash-lite-latest')

def calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia='', altitud=None):
    """
    Motor Agronómico Edafológico Offline de TierSystem.
    Evalúa matemáticamente los parámetros de suelo contra los rangos óptimos
    de los cultivos del Huila registrados en la tabla cultivos_cultivo.
    Funciona 100% offline sin depender de Google Gemini ni APIs externas.
    """
    cultivos = Cultivo.objects.filter(activo=True)
    if not cultivos.exists():
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

    evaluaciones = []
    preferencia_lower = preferencia.lower().strip() if preferencia else ''

    for cultivo in cultivos:
        puntajes = []
        
        # 1. Evaluación de pH (Ponderación 25%)
        ph_min = float(cultivo.ph_min)
        ph_max = float(cultivo.ph_max)
        if ph > 0:
            if ph_min <= ph <= ph_max:
                score_ph = 100.0
            elif ph < ph_min:
                diff = ph_min - ph
                score_ph = max(20.0, 100.0 - (diff / 1.5) * 80.0)
            else:
                diff = ph - ph_max
                score_ph = max(20.0, 100.0 - (diff / 1.5) * 80.0)
            puntajes.append(('ph', score_ph, 0.25))

        # 2. Evaluación de Nitrógeno (15%)
        n_min = float(cultivo.nitrogeno_min)
        n_max = float(cultivo.nitrogeno_max)
        if n > 0:
            if n_min <= n <= n_max:
                score_n = 100.0
            elif n < n_min:
                score_n = max(30.0, 100.0 - ((n_min - n) / max(n_min, 1)) * 70.0)
            else:
                score_n = max(60.0, 100.0 - ((n - n_max) / max(n_max, 1)) * 40.0)
            puntajes.append(('n', score_n, 0.15))

        # 3. Evaluación de Fósforo (15%)
        p_min = float(cultivo.fosforo_min)
        p_max = float(cultivo.fosforo_max)
        if p > 0:
            if p_min <= p <= p_max:
                score_p = 100.0
            elif p < p_min:
                score_p = max(30.0, 100.0 - ((p_min - p) / max(p_min, 1)) * 70.0)
            else:
                score_p = max(60.0, 100.0 - ((p - p_max) / max(p_max, 1)) * 40.0)
            puntajes.append(('p', score_p, 0.15))

        # 4. Evaluación de Potasio (15%)
        k_min = float(cultivo.potasio_min)
        k_max = float(cultivo.potasio_max)
        if k > 0:
            if k_min <= k <= k_max:
                score_k = 100.0
            elif k < k_min:
                score_k = max(30.0, 100.0 - ((k_min - k) / max(k_min, 1)) * 70.0)
            else:
                score_k = max(60.0, 100.0 - ((k - k_max) / max(k_max, 1)) * 40.0)
            puntajes.append(('k', score_k, 0.15))

        # 5. Conductividad Eléctrica (10%)
        c_min = float(cultivo.conductividad_min)
        c_max = float(cultivo.conductividad_max)
        if c > 0:
            if c_min <= c <= c_max:
                score_c = 100.0
            elif c < c_min:
                score_c = 85.0
            else:
                score_c = max(20.0, 100.0 - ((c - c_max) / max(c_max, 0.1)) * 80.0)
            puntajes.append(('c', score_c, 0.10))

        # 6. Humedad y Temperatura (10% c/u)
        h_min = float(cultivo.humedad_min)
        h_max = float(cultivo.humedad_max)
        if h > 0:
            score_h = 100.0 if (h_min <= h <= h_max) else max(40.0, 80.0)
            puntajes.append(('h', score_h, 0.10))

        t_min = float(cultivo.temperatura_min)
        t_max = float(cultivo.temperatura_max)
        if t > 0:
            score_t = 100.0 if (t_min <= t <= t_max) else max(40.0, 80.0)
            puntajes.append(('t', score_t, 0.10))

        # 7. Altitud (msnm) si está disponible (15%)
        if altitud and altitud > 0:
            alt_min = float(cultivo.altitud_min)
            alt_max = float(cultivo.altitud_max)
            if alt_min <= altitud <= alt_max:
                score_alt = 100.0
            else:
                diff_alt = min(abs(altitud - alt_min), abs(altitud - alt_max))
                score_alt = max(20.0, 100.0 - (diff_alt / 500.0) * 80.0)
            puntajes.append(('alt', score_alt, 0.15))

        if puntajes:
            peso_total = sum(p[2] for p in puntajes)
            compatibilidad = sum(p[1] * p[2] for p in puntajes) / peso_total
        else:
            compatibilidad = 50.0

        compat_final = round(float(compatibilidad), 1)

        # Plan de fertilización y recomendaciones agronómicas locales
        planes = []
        if ph > 0 and ph < ph_min:
            planes.append("Aplicar enmienda calcárea (Cal Dolomita o Cal Agrícola) para corregir acidez.")
        if n > 0 and n < n_min:
            planes.append("Reforzar Nitrógeno con materia orgánica compostada o fertilización nitrogenada fraccionada.")
        if p > 0 and p < p_min:
            planes.append("Aplicar Fósforo localizado (DAP o Roca Fosfórica) para estimular desarrollo radicular.")
        if k > 0 and k < k_min:
            planes.append("Suplir Potasio (KCl o Sulfato de Potasio) para llenado de fruto y resistencia hídrica.")
        if not planes:
            planes.append("Condiciones nutricionales óptimas. Mantener plan de fertilización estándar.")

        es_preferido = preferencia_lower and (preferencia_lower in cultivo.nombre.lower() or cultivo.nombre.lower() in preferencia_lower)

        evaluaciones.append({
            "cultivo": cultivo.nombre,
            "compatibilidad": compat_final,
            "viabilidad": "Alta" if compat_final >= 75 else ("Media" if compat_final >= 50 else "Baja"),
            "descripcion": f"{cultivo.descripcion[:160]}..." if cultivo.descripcion else f"Variedad adaptada al Huila en clima {cultivo.clima}.",
            "plan_fertilizacion": " ".join(planes),
            "es_preferido": bool(es_preferido)
        })

    evaluaciones.sort(key=lambda x: (1 if x['es_preferido'] else 0, x['compatibilidad']), reverse=True)
    top_recomendaciones = evaluaciones[:3]

    consejos = []
    if ph < 5.5 and ph > 0:
        consejos.append(f"El suelo presenta acidez (pH {ph:.1f}), común en suelos del Huila. Se recomienda encalar.")
    elif ph > 7.5:
        consejos.append(f"El suelo es ligeramente alcalino (pH {ph:.1f}). Monitorear microelementos.")
    else:
        consejos.append(f"El pH ({ph:.1f}) se encuentra en un rango balanceado para cultivos del Huila.")

    if n > 0 and p > 0 and k > 0:
        consejos.append(f"Perfil NPK registrado: N={n:.0f}, P={p:.0f}, K={k:.0f} mg/kg. Balance nutricional general evaluado.")
    else:
        consejos.append("Algunos macronutrientes no fueron detectados por la sonda; se consideraron las lecturas disponibles.")

    consejos.append("Diagnóstico agronómico generado 100% en modo offline.")

    return {
        "recomendaciones": top_recomendaciones,
        "consejo_general": " ".join(consejos),
        "modo": "offline"
    }


def api_obtener_cultivos(request):
    """
    Retorna la lista completa de cultivos con sus rangos ideales.
    Esto permite a la PWA descargar el catálogo para el MODO OFFLINE.
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
    Diagnóstico Agronómico Dual (ONLINE con Gemini o OFFLINE con Motor Edafológico).
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
        modo_solicitado = data.get("modo", "auto") # 'auto', 'online', 'offline'

        # Si se solicita explícitamente modo offline:
        if modo_solicitado == 'offline':
            resultado_offline = calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia=preferencia)
            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_offline, h, t, c, ph, n, p, k)
            return JsonResponse({"estado": "ok", "diagnostico": resultado_offline, "modo": "offline"})

        # MODO ONLINE: Intentar con Gemini si hay API Key disponible
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or genai is None:
            # Fallback inteligente al motor edafológico offline
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
3. IMPORTANTE: Si algunos parámetros están en 0 o faltan, asume que no fueron medidos. AUN ASÍ DEBES dar una recomendación o análisis basado en los datos que sí están disponibles.
4. Devuelve estrictamente el resultado en formato JSON válido (sin markdown ```json) con la siguiente estructura:
{{
  "recomendaciones": [
    {{
      "cultivo": "Nombre del Cultivo (Variedad)",
      "compatibilidad": 85,
      "descripcion": "Razón breve de por qué es adecuado o inadecuado."
    }}
  ],
  "consejo_general": "Un consejo general sobre fertilización o riego, y menciona si faltan datos relevantes."
}}
"""
            response = model.generate_content(prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            resultado_json = json.loads(text.strip())
            resultado_json["modo"] = "ia"

            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_json, h, t, c, ph, n, p, k)

            return JsonResponse({"estado": "ok", "diagnostico": resultado_json, "modo": "ia"})

        except Exception as gemini_error:
            # Si Gemini falla (ej. sin internet en campo, timeout, quota), fallback al motor offline local
            resultado_offline = calcular_diagnostico_edafologico(h, t, c, ph, n, p, k, preferencia=preferencia)
            resultado_offline["aviso"] = "Se activó el motor agronómico offline debido a interrupción de internet."
            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, resultado_offline, h, t, c, ph, n, p, k)
            return JsonResponse({"estado": "ok", "diagnostico": resultado_offline, "modo": "offline"})

    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)


@login_required(login_url='login')
def api_promedio_puntos(request):
    """
    Calcula el promedio de los puntos tomados para una solicitud de análisis.
    Solo el laboratorista asignado puede consultar los promedios.
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
            # Si no hay puntos tomados en mapa o es modalidad de muestra traída al laboratorio
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
    HU-0031: Compartir los resultados del análisis con el agricultor.
    Guarda o actualiza RegistroAnalisis y marca la Solicitud como COMPLETADA.
    Solo el laboratorista asignado puede compartir el resultado.
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

        # Verificar que el laboratorista asignado es quien llama
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
    HU-0032: Sincronización automática de análisis tomados en modo offline a MySQL.
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
                    # Solo completar solicitudes en estado válido para evitar modificaciones indebidas
                    if sol.estado not in ('ASIGNADA', 'EN_PROCESO', 'COMPLETADA'):
                        continue
                        
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
                    
                    # Sincronizar también puntos individuales en la tabla PuntoMuestreo si vienen
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


@login_required(login_url='login')
@csrf_exempt
def api_consultar_ia_agricultor(request):
    """
    Permite al agricultor consultar compatibilidad de un cultivo específico
    utilizando los parámetros de suelo registrados en su análisis completado.
    Solo el agricultor dueño del análisis puede consultar.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)
        
    try:
        data = json.loads(request.body)
        solicitud_id = data.get("solicitud_id")
        cultivo_busqueda = data.get("cultivo", "").strip()
        
        if not solicitud_id or not cultivo_busqueda:
            return JsonResponse({"estado": "error", "mensaje": "Faltan datos de consulta"}, status=400)
            
        from apps.analisis.models import RegistroAnalisis
        # Verificar ownership — solo el agricultor dueño puede consultar su análisis
        from django.db.models import Q
        analisis = RegistroAnalisis.objects.get(
            Q(solicitud__agricultor=request.user) |
            Q(solicitud__laboratorista_asignado=request.user),
            solicitud_id=solicitud_id,
        )
        
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai is not None:
            try:
                genai.configure(api_key=api_key)
                model = obtener_modelo_gemini()
                prompt = f"""
Eres un ingeniero agrónomo experto en suelos del departamento del Huila, Colombia.
El agricultor desea consultar si su lote '{analisis.solicitud.terreno.nombre}' es apto para cultivar: '{cultivo_busqueda}'.
Los parámetros reales medidos con sensor en su terreno son:
- Humedad: {analisis.humedad}%
- pH: {analisis.ph}
- Nitrógeno: {analisis.nitrogeno} mg/kg
- Fósforo: {analisis.fosforo} mg/kg
- Potasio: {analisis.potasio} mg/kg
- Conductividad Eléctrica: {analisis.conductividad} us/cm
- Temperatura: {analisis.temperatura} °C

Responde estrictamente en formato JSON válido (sin markdown ```json):
{{
  "cultivo": "{cultivo_busqueda}",
  "compatibilidad": 80,
  "descripcion": "Análisis agronómico detallado y real de viabilidad para esta zona andina/huilense considerando estos nutrientes y pH exactos.",
  "recomendacion_suelo": "Qué enmienda orgánica o química (cal, materia orgánica), ajuste de riego o fertilización NPK específica requiere este suelo para alcanzar máxima producción de {cultivo_busqueda}."
}}
"""
                res = model.generate_content(prompt)
                raw_text = res.text.strip()
                # Extraer JSON de forma segura
                inicio = raw_text.find('{')
                fin = raw_text.rfind('}')
                if inicio != -1 and fin != -1:
                    clean_text = raw_text[inicio:fin+1]
                else:
                    clean_text = raw_text.replace("```json", "").replace("```", "").strip()
                evaluacion = json.loads(clean_text)
            except Exception as ex:
                import traceback
                print(f"[GEMINI ERROR en consulta]: {ex}")
                traceback.print_exc()
                evaluacion = None
        else:
            evaluacion = None

        if not evaluacion:
            # Fallback matemático inteligente basado en rangos
            ph_val = float(analisis.ph)
            n_val = float(analisis.nitrogeno)
            compat = 85 if (5.5 <= ph_val <= 6.8 and n_val > 100) else (65 if (5.0 <= ph_val <= 7.2) else 45)
            evaluacion = {
                "cultivo": cultivo_busqueda,
                "compatibilidad": compat,
                "descripcion": f"Evaluado con los nutrientes registrados en tu predio (pH {analisis.ph}, N {analisis.nitrogeno}mg/kg, P {analisis.fosforo}mg/kg, K {analisis.potasio}mg/kg). Ofrece condiciones {'óptimas y de alto rendimiento' if compat >= 80 else ('favorables con plan de fertilización' if compat >= 60 else 'requiere acondicionamiento previo del pH')}.",
                "recomendacion_suelo": f"Para {cultivo_busqueda}, mantén una humedad cercana al 60% y refuerza la materia orgánica para facilitar la absorción de N-P-K."
            }
            
        return JsonResponse({"estado": "ok", "evaluacion": evaluacion})
    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)

