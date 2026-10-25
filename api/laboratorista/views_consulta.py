import json
import os

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.permissions import IsLaboratorista
from apps.analisis.models import RegistroAnalisis
from apps.cultivos.models import Cultivo
from apps.ia_recomendaciones import views as ia


@api_view(['POST'])
@permission_classes([IsLaboratorista])
def consulta_cultivo_view(request, solicitud_id):
    """
    POST /api/v1/laboratorista/resultados/<id>/consulta-cultivo/
    Body: {"cultivo": "Café Castillo"}
    El porcentaje se calcula con los rangos del catálogo (no lo inventa la IA).
    Gemini solo redacta la explicación; si falla, se responde con texto calculado.
    """
    cultivo_busqueda = str(request.data.get('cultivo', '')).strip()
    if not cultivo_busqueda:
        return Response({'error': 'Escribe el cultivo que quieres consultar.'}, status=400)

    try:
        analisis = RegistroAnalisis.objects.select_related(
            'solicitud__terreno'
        ).get(
            solicitud_id=solicitud_id,
            solicitud__laboratorista_asignado=request.user,
        )
    except RegistroAnalisis.DoesNotExist:
        return Response({'error': 'Análisis no encontrado.'}, status=404)

    # 1) Cultivo en el catálogo (sin tildes ni mayúsculas)
    q = ia._norm(cultivo_busqueda)
    catalogo = list(Cultivo.objects.filter(activo=True).order_by('nombre'))
    cultivo = next((c for c in catalogo if ia._norm(c.nombre) == q), None) \
        or next((c for c in catalogo if q in ia._norm(c.nombre)), None)

    # 2) Porcentaje real
    compat, detalle = (None, [])
    if cultivo:
        compat, detalle = ia.puntuar_cultivo(
            cultivo, analisis.humedad, analisis.temperatura, analisis.conductividad,
            analisis.ph, analisis.nitrogeno, analisis.fosforo, analisis.potasio,
        )
    nombre_cultivo = cultivo.nombre if cultivo else cultivo_busqueda

    # 3) Explicación con Gemini (opcional)
    texto = None
    fuente = 'calculo'
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key and ia.genai is not None:
        try:
            ia.genai.configure(api_key=api_key)
            model = ia.obtener_modelo_gemini()
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
            raw = model.generate_content(prompt).text.strip()
            ini, fin = raw.find('{'), raw.rfind('}')
            texto = json.loads(raw[ini:fin + 1] if ini != -1 and fin != -1 else raw)
            if texto.get('descripcion'):
                fuente = 'ia'
            else:
                texto = None
        except Exception as ex:
            print(f"[GEMINI ERROR en consulta lab]: {ex}")
            texto = None

    # 4) Respaldo sin IA, también con datos reales
    if not texto:
        if compat is not None:
            fuera = [d.split(' (')[0] for d in detalle if 'dentro' not in d]
            texto = {
                'descripcion': f"Compatibilidad calculada con los rangos de {nombre_cultivo}. "
                               + ('Todos los parámetros medidos están en rango.' if not fuera
                                  else 'Fuera de rango: ' + ', '.join(fuera) + '.'),
                'recomendacion_suelo': '; '.join(d for d in detalle if 'dentro' not in d)
                                       or 'Mantener el plan de fertilización estándar.',
            }
        else:
            texto = {
                'descripcion': f"'{nombre_cultivo}' no está en el catálogo de cultivos, "
                               'por eso no se puede calcular un porcentaje real.',
                'recomendacion_suelo': 'Pide al administrador que registre sus rangos de suelo.',
            }

    return Response({
        'cultivo': nombre_cultivo,
        'compatibilidad': compat,
        'descripcion': texto.get('descripcion', ''),
        'recomendacion_suelo': texto.get('recomendacion_suelo', ''),
        'fuente': fuente,
    })