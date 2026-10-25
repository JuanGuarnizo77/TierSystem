"""
Controladores de Ingesta y Procesamiento de Señales IoT de Sensores.
===================================================================
Gestiona la comunicación con el hardware de campo (ESP32 + RS485 + Sensor NPK):
  1. Ingesta de tramas crudas (`recibir_datos_sensor`) con desescalado Modbus y
     autenticación por cabecera `X-API-Key`.
  2. Filtro anti-ruido por ventana temporal (`captura_estable`), que calcula la
     moda o mediana de las lecturas tomadas en los últimos 15 segundos para
     anular picos transitorios y ruido de inserción de electrodos.
  3. Fijación y georreferenciación 3D del punto de muestreo (`guardar_punto`)
     asociado a la solicitud de análisis del laboratorista.
"""

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
    Endpoint HTTP: POST /sensores/lecturas/
    --------------------------------------
    Recibe la trama JSON periódica emitida por el microcontrolador ESP32 de campo.

    Seguridad:
      - En entornos de producción (`DEBUG=False`), exige la cabecera `X-API-Key`
        coincidente con la variable de configuración `SENSOR_API_KEY`.

    Desescalado Físico Modbus RTU:
      Los sensores industriales transmiten registros enteros de 16 bits sin coma flotante:
        - Humedad: valor / 10.0 (ej. 685 -> 68.5%)
        - Temperatura: valor / 10.0 (ej. 242 -> 24.2 °C)
        - pH: valor / 10.0 (ej. 62 -> pH 6.2)
        - CE, N, P, K: se reciben como enteros directos en µS/cm y mg/kg.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permiten peticiones POST"}, status=405)

    # Verificación de la clave de autenticación del dispositivo embebido
    api_key = request.headers.get('X-API-Key', '')
    if not settings.DEBUG and api_key != getattr(settings, 'SENSOR_API_KEY', ''):
        return JsonResponse({'error': 'No autorizado'}, status=401)

    try:
        datos = json.loads(request.body)

        # Aplicación de factores de escala según el mapeo de registros Modbus RTU
        humedad = float(datos.get("humedad", 0)) / 10.0
        temperatura = float(datos.get("temperatura", 0)) / 10.0
        conductividad = float(datos.get("conductividad", 0))
        ph = float(datos.get("ph", 0)) / 10.0
        nitrogeno = float(datos.get("nitrogeno", 0))
        fosforo = float(datos.get("fosforo", 0))
        potasio = float(datos.get("potasio", 0))

        # Almacenamiento en el buffer temporal de telemetría
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
    Endpoint HTTP: GET /sensores/captura-estable/
    --------------------------------------------
    Filtro digital de estabilización estadística de señales edafológicas.

    Problema abordado:
      Al insertar las sondas metálicas en el terreno ocurren transitorios capacitivos,
      micro-vibraciones y ruido de contacto durante los primeros segundos.

    Solución algorítmica:
      1. Extrae todas las lecturas registradas en una ventana móvil de los últimos 15 segundos.
      2. Si el búfer está vacío, notifica que el sensor está apagado o fuera de cobertura.
      3. Para cada variable física/química calcula la MODA estadística (`statistics.mode`).
         En señales Modbus digitales, la moda aísla el valor real repetitivo frente a picos atípicos.
      4. Si no existe moda única debido a dispersión continua, conmuta a la MEDIANA (`statistics.median`).
    """
    # Ventana móvil de tiempo de 15 segundos para asegurar estabilización
    tiempo_limite = timezone.now() - timedelta(seconds=15)
    lecturas = LecturaSensor.objects.filter(timestamp__gte=tiempo_limite)

    if not lecturas.exists():
        return JsonResponse({
            "estado": "error",
            "mensaje": "No se recibieron datos del sensor en los últimos 10 segundos. Asegúrate de que el ESP32 esté encendido y conectado."
        })

    # Extracción de series temporales independientes por parámetro
    h_list = [l.humedad for l in lecturas]
    t_list = [l.temperatura for l in lecturas]
    c_list = [l.conductividad for l in lecturas]
    ph_list = [l.ph for l in lecturas]
    n_list = [l.nitrogeno for l in lecturas]
    p_list = [l.fosforo for l in lecturas]
    k_list = [l.potasio for l in lecturas]

    def obtener_moda(datos):
        """Calcula la moda estadística con degradación elegante a la mediana."""
        try:
            return statistics.mode(datos)
        except statistics.StatisticsError:
            return statistics.median(datos)

    # Estructura de datos limpia y filtrada
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
    """
    Endpoint HTTP: POST /sensores/punto/<punto_id>/guardar/
    -------------------------------------------------------
    Persiste las lecturas estabilizadas y las coordenadas GNSS (lat, lon, altitud)
    en una estación específica de la cuadrícula de muestreo (`PuntoMuestreo`).

    Seguridad y Autorización:
      - Requiere sesión de laboratorista activa.
      - Valida que el punto pertenezca a una solicitud formalmente asignada al usuario
        autenticado (`solicitud__laboratorista_asignado=request.user`), previniendo
        escrituras no autorizadas o interferencias entre técnicos de campo.
    """
    if request.method == "POST":
        from apps.analisis.models import PuntoMuestreo
        from django.utils import timezone
        try:
            datos = json.loads(request.body)

            # Validación de pertenencia estricta del punto de muestreo al técnico asignado
            punto = PuntoMuestreo.objects.get(
                id=punto_id,
                solicitud__laboratorista_asignado=request.user
            )

            # Asignación de variables fisicoquímicas medidas
            punto.humedad = datos.get("humedad")
            punto.temperatura = datos.get("temperatura")
            punto.conductividad = datos.get("conductividad")
            punto.ph = datos.get("ph")
            punto.nitrogeno = datos.get("nitrogeno")
            punto.fosforo = datos.get("fosforo")
            punto.potasio = datos.get("potasio")

            # Georreferenciación 3D satelital (latitud, longitud y altitud barométrica/GPS)
            if datos.get("latitud") is not None:
                punto.latitud = datos.get("latitud")
            if datos.get("longitud") is not None:
                punto.longitud = datos.get("longitud")
            if datos.get("altitud") is not None:
                punto.altitud = datos.get("altitud")

            # Transición de estado a 'TOMADO' con estampa temporal actual
            punto.fecha_toma = timezone.now()
            punto.estado = 'TOMADO'
            punto.save()

            return JsonResponse({"estado": "ok", "mensaje": "Punto guardado exitosamente en base de datos"})
        except Exception as e:
            return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)

    return JsonResponse({"estado": "error"}, status=400)
