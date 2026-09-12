import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CultivoIdeal

# Intentar importar google.generativeai, manejando si aún no está instalado
try:
    import google.generativeai as genai
except ImportError:
    genai = None

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

@csrf_exempt
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
        api_key = "AQ.Ab8RN6JX8hwmOQYvJblYdZZ2J-PnS1RwUUpW10xuN_gmDsBIXg"
        
        if not api_key:
            # MOCK Dinámico basado en los datos si no hay API KEY
            if n == 0 and p == 0 and k == 0:
                mock_response = {
                    "recomendaciones": [
                        {
                            "cultivo": "Ninguno (Suelo Inerte)",
                            "compatibilidad": 0,
                            "descripcion": "No se detectan nutrientes (NPK en 0). Parece que el sensor está al aire o el suelo está completamente estéril."
                        }
                    ],
                    "consejo_general": f"La humedad es {h}% y el pH {ph}. Necesitas insertar el sensor en tierra real para obtener lecturas de Nitrógeno, Fósforo y Potasio."
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
            return JsonResponse({"estado": "ok", "diagnostico": mock_response})
            
        # Recibir preferencia si existe
        preferencia = data.get("preferencia", "").strip()

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.6-flash')
        
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
3. Devuelve estrictamente el resultado en formato JSON válido (sin markdown ```json) con la siguiente estructura:
{{
  "recomendaciones": [
    {{
      "cultivo": "Nombre del Cultivo (Variedad)",
      "compatibilidad": 85, // número de 0 a 100
      "descripcion": "Razón breve de por qué es adecuado o inadecuado."
    }}
  ],
  "consejo_general": "Un consejo general sobre fertilización o riego."
}}
"""

        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        
        resultado_json = json.loads(text.strip())
        
        # Guardar historial si viene de una solicitud
        solicitud_id = data.get("solicitud_id")
        if solicitud_id:
            from apps.solicitudes.models import SolicitudAnalisis
            from apps.analisis.models import RegistroAnalisis
            try:
                sol = SolicitudAnalisis.objects.get(id=solicitud_id)
                # Crear o actualizar el registro
                RegistroAnalisis.objects.update_or_create(
                    solicitud=sol,
                    defaults={
                        'humedad': h,
                        'temperatura': t,
                        'conductividad': c,
                        'ph': ph,
                        'nitrogeno': n,
                        'fosforo': p,
                        'potasio': k,
                        'diagnostico_ia': json.dumps(resultado_json)
                    }
                )
                # Marcar solicitud como completada
                sol.estado = 'COMPLETADA'
                sol.save()
            except SolicitudAnalisis.DoesNotExist:
                pass
        
        return JsonResponse({"estado": "ok", "diagnostico": resultado_json})

    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)
