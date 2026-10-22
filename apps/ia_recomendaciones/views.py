import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import CultivoIdeal

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
    from apps.ia_recomendaciones.models import CultivoIdeal
    
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
        
        cultivo_obj = CultivoIdeal.objects.filter(nombre__icontains=nombre_limpio).first()
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
    for nombre in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
        try:
            return genai.GenerativeModel(nombre)
        except Exception:
            continue
    return genai.GenerativeModel('gemini-1.5-flash')

def api_obtener_cultivos(request):
    """
    Retorna la lista completa de cultivos con sus rangos ideales.
    Esto permite a la PWA descargar el catálogo para el MODO OFFLINE.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Solo GET permitido"}, status=405)
    
    cultivos = CultivoIdeal.objects.all()
    datos = [c.to_dict() for c in cultivos]
    
    return JsonResponse({
        "estado": "ok",
        "cultivos": datos
    })

@login_required(login_url='login')
def api_diagnosticar_ia(request):
    """
    MODO ONLINE:
    Envía los 7 parámetros a Google Gemini y pide un diagnóstico json.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo POST permitido"}, status=405)
    
    if genai is None:
        return JsonResponse({"error": "El paquete google-generativeai no está instalado en el servidor."}, status=500)

    try:
        data = json.loads(request.body)
        h = data.get("humedad", 0)
        t = data.get("temperatura", 0)
        c = data.get("conductividad", 0)
        ph = data.get("ph", 0)
        n = data.get("nitrogeno", 0)
        p = data.get("fosforo", 0)
        k = data.get("potasio", 0)

        # Configurar la API Key de Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            # MOCK Dinámico basado en los datos si no hay API KEY
            if n == 0 and p == 0 and k == 0:
                mock_response = {
                    "recomendaciones": [
                        {
                            "cultivo": "Cultivo sugerido (Basado en datos parciales)",
                            "compatibilidad": 70,
                            "descripcion": "Faltan lecturas de nutrientes (NPK), pero según la humedad y pH registrados, este cultivo podría adaptarse."
                        }
                    ],
                    "consejo_general": f"La humedad es {h}% y el pH {ph}. Sería ideal registrar Nitrógeno, Fósforo y Potasio para un análisis completo."
                }
            else:
                mock_response = {
                    "recomendaciones": [
                        {
                            "cultivo": "Café (IA MOCK)",
                            "compatibilidad": 92,
                            "descripcion": f"Con {n}mg/kg de Nitrógeno y pH de {ph}, las condiciones son excelentes."
                        },
                        {
                            "cultivo": "Tomate (IA MOCK)",
                            "compatibilidad": 78,
                            "descripcion": f"La humedad del {h}% es adecuada para evitar hongos en las raíces."
                        }
                    ],
                    "consejo_general": "Te recomendamos mantener el monitoreo. Los niveles son aceptables."
                }
            # Guardar historial si viene de una solicitud en modo mock
            solicitud_id = data.get("solicitud_id")
            if solicitud_id:
                _guardar_diagnostico_solicitud(solicitud_id, mock_response, h, t, c, ph, n, p, k)

            return JsonResponse({"estado": "ok", "diagnostico": mock_response})
            
        # Recibir preferencia si existe
        preferencia = data.get("preferencia", "").strip()

        genai.configure(api_key=api_key)
        model = obtener_modelo_gemini()
        
        # Lógica de prompt basada en la preferencia y región
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
3. IMPORTANTE: Si algunos parámetros están en 0 o faltan, asume que no fueron medidos. AUN ASÍ DEBES dar una recomendación o análisis basado en los datos que sí están disponibles (no digas que el suelo es inerte a menos que estés seguro). Indica en el consejo_general qué datos faltarían para un análisis más completo.
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
        
        # Guardar historial y recomendaciones relacionales en BD si viene de una solicitud
        solicitud_id = data.get("solicitud_id")
        if solicitud_id:
            _guardar_diagnostico_solicitud(solicitud_id, resultado_json, h, t, c, ph, n, p, k)
        
        return JsonResponse({"estado": "ok", "diagnostico": resultado_json})

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
        analisis = RegistroAnalisis.objects.get(
            solicitud_id=solicitud_id,
            solicitud__agricultor=request.user
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

