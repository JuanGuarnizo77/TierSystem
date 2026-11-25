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

import hmac
import json
import logging
import math
import statistics
from collections import Counter
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from core.permissions import tiene_rol
from core.utils import registrar_evento_seguridad
from .models import LecturaSensor

logger = logging.getLogger(__name__)

RANGOS_FISICOS_SENSOR = {
    'humedad': (0.0, 100.0),
    'temperatura': (-20.0, 80.0),
    'conductividad': (0.0, 20000.0),
    'ph': (0.0, 14.0),
    'nitrogeno': (0.0, 5000.0),
    'fosforo': (0.0, 5000.0),
    'potasio': (0.0, 5000.0),
}


def _validar_valor_rango(valor, nombre, minimo, maximo):
    """Valida que un valor numérico sea finito y esté dentro del rango físico permitido."""
    try:
        num = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El parámetro '{nombre}' debe ser numérico.")
    if not math.isfinite(num) or num < minimo or num > maximo:
        raise ValueError(
            f"El parámetro '{nombre}' ({num}) está fuera del rango físico permitido ({minimo} a {maximo})."
        )
    return round(num, 2)


@csrf_exempt
def recibir_datos_sensor(request):
    """
    Endpoint HTTP: POST /sensores/lecturas/
    --------------------------------------
    Recibe la trama JSON periódica emitida por el microcontrolador ESP32 de campo.

    Seguridad:
      - En entornos de producción (`DEBUG=False`), exige la cabecera `X-API-Key`
        coincidente con la variable de configuración `SENSOR_API_KEY` mediante
        comparación en tiempo constante (`hmac.compare_digest`).

    Desescalado Físico Modbus RTU:
      Los sensores industriales transmiten registros enteros de 16 bits sin coma flotante:
        - Humedad: valor / 10.0 (ej. 685 -> 68.5%)
        - Temperatura: valor / 10.0 (ej. 242 -> 24.2 °C)
        - pH: valor / 10.0 (ej. 62 -> pH 6.2)
        - CE, N, P, K: se reciben como enteros directos en µS/cm y mg/kg.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permiten peticiones POST"}, status=405)

    # Verificación de la clave de autenticación del dispositivo embebido en tiempo constante
    api_key = request.headers.get('X-API-Key', '') or ''
    expected_key = getattr(settings, 'SENSOR_API_KEY', '') or ''
    if not settings.DEBUG or (expected_key and api_key):
        if not expected_key or not hmac.compare_digest(
            api_key.encode('utf-8'), expected_key.encode('utf-8')
        ):
            registrar_evento_seguridad(
                request, 'SENSOR_API_KEY_INVALIDA',
                'Intento no autorizado de ingesta en /sensores/lecturas/', nivel='WARNING'
            )
            return JsonResponse({'error': 'No autorizado'}, status=401)

    try:
        datos = json.loads(request.body)
        if not isinstance(datos, dict):
            return JsonResponse({"estado": "error", "mensaje": "Formato de trama inválido"}, status=400)

        def _leer_escalado(clave, factor=1.0):
            val_raw = datos.get(clave)
            if val_raw is None:
                return None
            return _validar_valor_rango(float(val_raw) / factor, clave, *RANGOS_FISICOS_SENSOR[clave])

        # Aplicación de factores de escala según el mapeo de registros Modbus RTU (None = no medido)
        humedad = _leer_escalado("humedad", 10.0)
        temperatura = _leer_escalado("temperatura", 10.0)
        conductividad = _leer_escalado("conductividad", 1.0)
        ph = _leer_escalado("ph", 10.0)
        nitrogeno = _leer_escalado("nitrogeno", 1.0)
        fosforo = _leer_escalado("fosforo", 1.0)
        potasio = _leer_escalado("potasio", 1.0)

        bateria = None
        if datos.get("bateria") is not None:
            bateria = _validar_valor_rango(datos.get("bateria"), 'bateria', 0.0, 100.0)
        senal_rssi = None
        if datos.get("senal_rssi") is not None:
            senal_rssi = int(_validar_valor_rango(datos.get("senal_rssi"), 'senal_rssi', -120.0, 0.0))

        # Almacenamiento en el buffer temporal de telemetría
        LecturaSensor.objects.create(
            humedad=humedad,
            temperatura=temperatura,
            conductividad=conductividad,
            ph=ph,
            nitrogeno=nitrogeno,
            fosforo=fosforo,
            potasio=potasio,
            bateria=bateria,
            senal_rssi=senal_rssi,
        )

        return JsonResponse({
            "estado": "ok",
            "mensaje": "Datos recibidos correctamente"
        })

    except json.JSONDecodeError:
        return JsonResponse({"estado": "error", "mensaje": "JSON inválido"}, status=400)
    except ValueError as ve:
        return JsonResponse({"estado": "error", "mensaje": str(ve)}, status=400)
    except Exception:
        logger.exception("Error procesando trama de sensor IoT")
        return JsonResponse({"estado": "error", "mensaje": "Error interno al procesar la lectura del sensor."}, status=500)


@login_required(login_url='login')
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
      3. Para cada variable física/química usa la MODA: el valor que más se repite.
         En señales Modbus digitales, la moda aísla el valor real repetitivo frente a picos atípicos.
      4. Si no hay moda clara (ningún valor se repite, o hay empate), usa la MEDIANA.
    """
    if request.method != "GET":
        return JsonResponse({"estado": "error", "mensaje": "Método no permitido."}, status=405)

    if not tiene_rol(request.user, 'LABORATORISTA', 'ADMIN'):
        registrar_evento_seguridad(
            request, 'ACCESO_DENEGADO_SENSOR',
            'Usuario sin rol LABORATORISTA intentó leer captura_estable', nivel='WARNING'
        )
        return JsonResponse({"estado": "error", "mensaje": "No tiene permisos para consultar telemetría de laboratorio."}, status=403)

    # Ventana móvil de tiempo de 15 segundos para asegurar estabilización
    tiempo_limite = timezone.now() - timedelta(seconds=15)
    lecturas = LecturaSensor.objects.filter(timestamp__gte=tiempo_limite)

    if not lecturas.exists():
        return JsonResponse({
            "estado": "error",
            "mensaje": "No se recibieron datos del sensor en los últimos 15 segundos. Asegúrate de que el ESP32 esté encendido y conectado."
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
        """Devuelve la moda si es clara; si no, la mediana, ignorando lecturas nulas."""
        validos = [d for d in datos if d is not None]
        if not validos:
            return None
        conteo = Counter(validos).most_common()
        # Moda clara: el valor más repetido, repetido más de una vez y sin empate.
        if conteo[0][1] > 1 and (len(conteo) == 1 or conteo[0][1] > conteo[1][1]):
            return conteo[0][0]
        return statistics.median(validos)

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
def guardar_punto(request, punto_id):
    """
    Endpoint HTTP: POST /sensores/punto/<punto_id>/guardar/
    -------------------------------------------------------
    Persiste las lecturas estabilizadas y las coordenadas GNSS (lat, lon, altitud)
    en una estación específica de la cuadrícula de muestreo (`PuntoMuestreo`).

    Seguridad y Autorización:
      - Requiere sesión de laboratorista activa y token CSRF válido.
      - Valida que el punto pertenezca a una solicitud formalmente asignada al usuario
        autenticado (`solicitud__laboratorista_asignado=request.user`), previniendo
        escrituras no autorizadas o interferencias entre técnicos de campo.
    """
    if request.method != "POST":
        return JsonResponse({"estado": "error", "mensaje": "Método no permitido."}, status=405)

    if not tiene_rol(request.user, 'LABORATORISTA', 'ADMIN'):
        registrar_evento_seguridad(
            request, 'ACCESO_DENEGADO_GUARDAR_PUNTO',
            f'Intento sin rol autorizado sobre punto_id={punto_id}', nivel='WARNING'
        )
        return JsonResponse({"estado": "error", "mensaje": "No autorizado."}, status=403)

    from apps.analisis.models import PuntoMuestreo
    try:
        datos = json.loads(request.body)
        if not isinstance(datos, dict):
            return JsonResponse({"estado": "error", "mensaje": "Cuerpo JSON inválido."}, status=400)

        # Validación de pertenencia estricta del punto de muestreo al técnico asignado
        try:
            punto = PuntoMuestreo.objects.get(
                id=punto_id,
                solicitud__laboratorista_asignado=request.user
            )
        except PuntoMuestreo.DoesNotExist:
            registrar_evento_seguridad(
                request, 'IDOR_PUNTO_MUESTREO',
                f'Intento de acceso a punto_id={punto_id} no asignado al usuario', nivel='WARNING'
            )
            return JsonResponse({"estado": "error", "mensaje": "Punto de muestreo no encontrado o no asignado."}, status=404)

        # Validación y asignación de variables fisicoquímicas medidas
        punto.humedad = _validar_valor_rango(datos.get("humedad"), 'humedad', *RANGOS_FISICOS_SENSOR['humedad'])
        punto.temperatura = _validar_valor_rango(datos.get("temperatura"), 'temperatura', *RANGOS_FISICOS_SENSOR['temperatura'])
        punto.conductividad = _validar_valor_rango(datos.get("conductividad"), 'conductividad', *RANGOS_FISICOS_SENSOR['conductividad'])
        punto.ph = _validar_valor_rango(datos.get("ph"), 'ph', *RANGOS_FISICOS_SENSOR['ph'])
        punto.nitrogeno = _validar_valor_rango(datos.get("nitrogeno"), 'nitrogeno', *RANGOS_FISICOS_SENSOR['nitrogeno'])
        punto.fosforo = _validar_valor_rango(datos.get("fosforo"), 'fosforo', *RANGOS_FISICOS_SENSOR['fosforo'])
        punto.potasio = _validar_valor_rango(datos.get("potasio"), 'potasio', *RANGOS_FISICOS_SENSOR['potasio'])

        # Georreferenciación 3D satelital (latitud, longitud y altitud barométrica/GPS)
        if datos.get("latitud") is not None:
            lat = float(datos.get("latitud"))
            if not math.isfinite(lat) or lat < -90.0 or lat > 90.0:
                return JsonResponse({"estado": "error", "mensaje": "Latitud fuera de rango (-90 a 90)."}, status=400)
            punto.latitud = round(lat, 7)
        if datos.get("longitud") is not None:
            lon = float(datos.get("longitud"))
            if not math.isfinite(lon) or lon < -180.0 or lon > 180.0:
                return JsonResponse({"estado": "error", "mensaje": "Longitud fuera de rango (-180 a 180)."}, status=400)
            punto.longitud = round(lon, 7)
        if datos.get("altitud") is not None:
            alt = float(datos.get("altitud"))
            if not math.isfinite(alt) or alt < -500.0 or alt > 9000.0:
                return JsonResponse({"estado": "error", "mensaje": "Altitud fuera de rango (-500 a 9000 msnm)."}, status=400)
            punto.altitud = round(alt, 2)

        # Transición de estado a 'TOMADO' con estampa temporal actual
        punto.fecha_toma = timezone.now()
        punto.estado = 'TOMADO'
        punto.save()

        return JsonResponse({"estado": "ok", "mensaje": "Punto guardado exitosamente en base de datos"})
    except json.JSONDecodeError:
        return JsonResponse({"estado": "error", "mensaje": "Formato JSON inválido."}, status=400)
    except ValueError as ve:
        return JsonResponse({"estado": "error", "mensaje": str(ve)}, status=400)
    except Exception:
        logger.exception("Error inesperado en guardar_punto")
        return JsonResponse({"estado": "error", "mensaje": "Error interno al guardar el punto de muestreo."}, status=500)
