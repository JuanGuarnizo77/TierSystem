import json
import statistics
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import LecturaSensor

@csrf_exempt
def recibir_datos_sensor(request):
    """
    Endpoint que recibe el JSON desde el ESP32
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permiten peticiones POST"}, status=405)

    api_key = request.headers.get('X-API-Key', '')
    if api_key != settings.SENSOR_API_KEY:
        return JsonResponse({'error': 'No autorizado'}, status=401)

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
    Endpoint invocado por el Dashboard después de 10s de espera.
    Obtiene todas las lecturas de los últimos 10 segundos y devuelve
    la MODA o PROMEDIO de las señales para garantizar estabilidad.
    Si no hay conexión con el sensor, devuelve datos simulados (del día anterior).
    """
    import random
    tiempo_limite = timezone.now() - timedelta(seconds=15) # 15s de gracia
    lecturas = LecturaSensor.objects.filter(timestamp__gte=tiempo_limite)

    if not lecturas.exists():
        return JsonResponse({
            "estado": "error",
            "mensaje": "No se recibieron datos del sensor en los últimos 10 segundos. Asegúrate de que el ESP32 esté encendido y conectado."
        })

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

@login_required(login_url='login')
@csrf_exempt
def guardar_punto(request, punto_id):
    if request.method == "POST":
        from apps.analisis.models import PuntoMuestreo
        from django.utils import timezone
        try:
            datos = json.loads(request.body)
            # Verificar que el punto pertenece a una solicitud asignada a este laboratorista
            punto = PuntoMuestreo.objects.get(
                id=punto_id,
                solicitud__laboratorista_asignado=request.user
            )
            punto.humedad = datos.get("humedad")
            punto.temperatura = datos.get("temperatura")
            punto.conductividad = datos.get("conductividad")
            punto.ph = datos.get("ph")
            punto.nitrogeno = datos.get("nitrogeno")
            punto.fosforo = datos.get("fosforo")
            punto.potasio = datos.get("potasio")
            
            # Nuevos campos de georreferenciación 3D
            if datos.get("latitud") is not None:
                punto.latitud = datos.get("latitud")
            if datos.get("longitud") is not None:
                punto.longitud = datos.get("longitud")
            if datos.get("altitud") is not None:
                punto.altitud = datos.get("altitud")
                
            punto.fecha_toma = timezone.now()
            punto.estado = 'TOMADO'
            punto.save()
            return JsonResponse({"estado": "ok", "mensaje": "Punto guardado exitosamente en base de datos"})
        except Exception as e:
            return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)
    return JsonResponse({"estado": "error"}, status=400)
