import json
import statistics
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import LecturaSensor

@csrf_exempt
def recibir_datos_sensor(request):
    """
    Endpoint que recibe el JSON desde el ESP32
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permiten peticiones POST"}, status=405)

    try:
        datos = json.loads(request.body)
        
        humedad = float(datos.get("humedad", 0)) / 10.0
        temperatura = float(datos.get("temperatura", 0)) / 10.0
        conductividad = float(datos.get("conductividad", 0))
        ph = float(datos.get("ph", 0)) / 10.0
        nitrogeno = float(datos.get("nitrogeno", 0))
        fosforo = float(datos.get("fosforo", 0))
        potasio = float(datos.get("potasio", 0))

        # Guardar en BD
        LecturaSensor.objects.create(
            humedad=humedad,
            temperatura=temperatura,
            conductividad=conductividad,
            ph=ph,
            nitrogeno=nitrogeno,
            fosforo=fosforo,
            potasio=potasio
        )

        return JsonResponse({
            "estado": "ok",
            "mensaje": "Datos recibidos correctamente"
        })

    except json.JSONDecodeError:
        return JsonResponse({"estado": "error", "mensaje": "JSON inválido"}, status=400)
    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)


def captura_estable(request):
    """
    Endpoint invocado por el Dashboard después de 20s de espera.
    Obtiene todas las lecturas de los últimos 20 segundos y devuelve
    la MODA o PROMEDIO de las señales para garantizar estabilidad.
    """
    tiempo_limite = timezone.now() - timedelta(seconds=25) # 25s de gracia
    lecturas = LecturaSensor.objects.filter(timestamp__gte=tiempo_limite)

    if not lecturas.exists():
        return JsonResponse({"estado": "error", "mensaje": "No se encontraron datos. ESP32 desconectado o sin enviar datos."})

    # Extraer arrays de cada variable
    h_list = [l.humedad for l in lecturas]
    t_list = [l.temperatura for l in lecturas]
    c_list = [l.conductividad for l in lecturas]
    ph_list = [l.ph for l in lecturas]
    n_list = [l.nitrogeno for l in lecturas]
    p_list = [l.fosforo for l in lecturas]
    k_list = [l.potasio for l in lecturas]

    # Calcular moda (o usar media si no hay moda clara para float)
    # Ya que los datos del sensor modbus suelen ser consistentes, la moda es perfecta para ruido
    def obtener_moda(datos):
        try:
            return statistics.mode(datos)
        except statistics.StatisticsError:
            # Si no hay moda única, devolvemos la mediana
            return statistics.median(datos)

    datos_estables = {
        "humedad": obtener_moda(h_list),
        "temperatura": obtener_moda(t_list),
        "conductividad": obtener_moda(c_list),
        "ph": obtener_moda(ph_list),
        "nitrogeno": obtener_moda(n_list),
        "fosforo": obtener_moda(p_list),
        "potasio": obtener_moda(k_list),
        "muestras_tomadas": len(lecturas)
    }

    return JsonResponse({
        "estado": "ok",
        "mensaje": "Conexión Exitosa. Datos estabilizados.",
        "datos": datos_estables
    })
