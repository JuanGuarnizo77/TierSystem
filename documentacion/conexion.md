conexiones del sstema.

Codigo de C++ para el sensor que ya esta en arduido IDE:

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiManager.h> // <-- NUEVA LIBRERÍA: Instálala en Arduino IDE

// ============================================================
// CONFIGURACIÓN DJANGO
// ============================================================

// Cambiar por la IP del computador donde está Django
// Ejemplo:
// http://192.168.1.100:8000/api/lecturas/

const char* DJANGO_URL = "http://192.168.1.100:8000/api/lecturas/";

// ============================================================
// PINES ESP32 + HW-097
// ============================================================

#define RS485_DI 2
#define RS485_DE 15
#define RS485_RE 13
#define RS485_RO 5

// ============================================================
// UART DEL ESP32
// ============================================================

// UART2
HardwareSerial RS485Serial(2);

// ============================================================
// CONFIGURACIÓN MODBUS
// ============================================================

#define SENSOR_ID 1

// ============================================================
// TIEMPO ENTRE LECTURAS
// ============================================================

const unsigned long INTERVALO = 5000;

unsigned long ultimaLectura = 0;


// ============================================================
// FUNCIONES RS485
// ============================================================

void modoTransmision()
{
  digitalWrite(RS485_DE, HIGH);
  digitalWrite(RS485_RE, HIGH);
}

void modoRecepcion()
{
  digitalWrite(RS485_DE, LOW);
  digitalWrite(RS485_RE, LOW);
}


// ============================================================
// CALCULAR CRC MODBUS
// ============================================================

uint16_t calcularCRC(uint8_t *buffer, uint8_t longitud)
{
  uint16_t crc = 0xFFFF;

  for (uint8_t pos = 0; pos < longitud; pos++)
  {
    crc ^= (uint16_t)buffer[pos];

    for (uint8_t i = 8; i != 0; i--)
    {
      if ((crc & 0x0001) != 0)
      {
        crc >>= 1;
        crc ^= 0xA001;
      }
      else
      {
        crc >>= 1;
      }
    }
  }

  return crc;
}


// ============================================================
// LEER REGISTROS MODBUS
// ============================================================

bool leerRegistros(uint16_t registroInicial,
                   uint16_t cantidad,
                   uint16_t *datos)
{
  uint8_t solicitud[8];

  solicitud[0] = SENSOR_ID;
  solicitud[1] = 0x03;
  solicitud[2] = highByte(registroInicial);
  solicitud[3] = lowByte(registroInicial);
  solicitud[4] = highByte(cantidad);
  solicitud[5] = lowByte(cantidad);

  uint16_t crc = calcularCRC(solicitud, 6);

  solicitud[6] = lowByte(crc);
  solicitud[7] = highByte(crc);

  // Limpiar buffer
  while (RS485Serial.available())
  {
    RS485Serial.read();
  }

  // Activar transmisión
  modoTransmision();

  delay(2);

  // Enviar solicitud
  RS485Serial.write(solicitud, 8);

  RS485Serial.flush();

  delay(2);

  // Activar recepción
  modoRecepcion();

  // ========================================================
  // RESPUESTA ESPERADA
  // ========================================================

  uint8_t respuesta[32];
  uint8_t indice = 0;

  unsigned long tiempoInicio = millis();

  while (millis() - tiempoInicio < 1000)
  {
    if (RS485Serial.available())
    {
      respuesta[indice++] = RS485Serial.read();

      if (indice >= sizeof(respuesta))
      {
        break;
      }
    }
  }

  // Mínimo:
  // ID + función + bytes + datos + CRC
  if (indice < 5)
  {
    Serial.println("ERROR: No se recibió respuesta del sensor.");
    return false;
  }

  // ========================================================
  // COMPROBAR ID
  // ========================================================

  if (respuesta[0] != SENSOR_ID)
  {
    Serial.println("ERROR: ID del sensor incorrecto.");
    return false;
  }

  // ========================================================
  // COMPROBAR FUNCIÓN
  // ========================================================

  if (respuesta[1] != 0x03)
  {
    Serial.println("ERROR: Función Modbus incorrecta.");
    return false;
  }

  uint8_t bytesDatos = respuesta[2];

  if (bytesDatos != cantidad * 2)
  {
    Serial.println("ERROR: Cantidad de datos incorrecta.");
    return false;
  }

  // ========================================================
  // EXTRAER REGISTROS
  // ========================================================

  for (uint16_t i = 0; i < cantidad; i++)
  {
    uint8_t posicion = 3 + (i * 2);

    datos[i] =
      ((uint16_t)respuesta[posicion] << 8) |
      respuesta[posicion + 1];
  }

  // ========================================================
  // COMPROBAR CRC
  // ========================================================

  uint16_t crcRecibido =
    respuesta[indice - 2] |
    ((uint16_t)respuesta[indice - 1] << 8);

  uint16_t crcCalculado =
    calcularCRC(respuesta, indice - 2);

  if (crcRecibido != crcCalculado)
  {
    Serial.println("ERROR: CRC incorrecto.");
    return false;
  }

  return true;
}


// ============================================================
// MOSTRAR DATOS
// ============================================================

void mostrarDatos(uint16_t *datos)
{
  Serial.println();
  Serial.println("=================================");
  Serial.println("      DATOS DEL SENSOR");
  Serial.println("=================================");

  Serial.print("Registro 0: ");
  Serial.println(datos[0]);

  Serial.print("Registro 1: ");
  Serial.println(datos[1]);

  Serial.print("Registro 2: ");
  Serial.println(datos[2]);

  Serial.print("Registro 3: ");
  Serial.println(datos[3]);

  Serial.print("Registro 4: ");
  Serial.println(datos[4]);

  Serial.print("Registro 5: ");
  Serial.println(datos[5]);

  Serial.print("Registro 6: ");
  Serial.println(datos[6]);

  Serial.println("=================================");
}


// ============================================================
// ENVIAR DATOS A DJANGO
// ============================================================

void enviarADjango(uint16_t *datos)
{
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi desconectado.");
    return;
  }

  HTTPClient http;

  Serial.println();
  Serial.println("Enviando datos a Django...");

  http.begin(DJANGO_URL);

  http.addHeader("Content-Type", "application/json");

  // ========================================================
  // JSON
  // ========================================================

  String json = "{";

  json += "\"humedad\":";
  json += String(datos[0]);

  json += ",";

  json += "\"temperatura\":";
  json += String(datos[1]);

  json += ",";

  json += "\"conductividad\":";
  json += String(datos[2]);

  json += ",";

  json += "\"ph\":";
  json += String(datos[3]);

  json += ",";

  json += "\"nitrogeno\":";
  json += String(datos[4]);

  json += ",";

  json += "\"fosforo\":";
  json += String(datos[5]);

  json += ",";

  json += "\"potasio\":";
  json += String(datos[6]);

  json += "}";

  Serial.println("JSON enviado:");

  Serial.println(json);

  // ========================================================
  // POST
  // ========================================================

  int codigoRespuesta = http.POST(json);

  Serial.print("Código HTTP: ");
  Serial.println(codigoRespuesta);

  if (codigoRespuesta > 0)
  {
    String respuesta = http.getString();

    Serial.println("Respuesta de Django:");

    Serial.println(respuesta);
  }
  else
  {
    Serial.print("Error enviando datos: ");
    Serial.println(http.errorToString(codigoRespuesta));
  }

  http.end();
}


// ============================================================
// CONECTAR WIFI (NUEVO MÉTODO DINÁMICO)
// ============================================================

void conectarWiFi()
{
  Serial.println();
  Serial.println("Iniciando Gestor de WiFi...");

  // Inicializar WiFiManager
  WiFiManager wifiManager;

  // Descomentar la siguiente línea si quieres borrar el WiFi guardado para probar
  // wifiManager.resetSettings();

  // Esto crea una red WiFi abierta llamada "TierSystem-Sensor"
  // Si el ESP32 no encuentra un WiFi conocido, emitirá esta red.
  // Conéctate a ella con tu celular, y automáticamente se abrirá un portal
  // para que escribas la contraseña de la nueva red.
  if (!wifiManager.autoConnect("TierSystem-Sensor")) {
    Serial.println("Error: No se pudo conectar al WiFi y se agotó el tiempo.");
    ESP.restart(); // Reiniciar si falla
    delay(1000);
  }

  Serial.println();
  Serial.println("¡WiFi conectado exitosamente!");
  Serial.print("IP del ESP32: ");
  Serial.println(WiFi.localIP());
}


// ============================================================
// SETUP
// ============================================================

void setup()
{
  Serial.begin(115200);

  // ========================================================
  // CONFIGURAR HW-097
  // ========================================================

  pinMode(RS485_DE, OUTPUT);
  pinMode(RS485_RE, OUTPUT);

  modoRecepcion();

  // ========================================================
  // UART RS485
  // ========================================================

  // RX = D5
  // TX = D2

  RS485Serial.begin(
    4800,
    SERIAL_8N1,
    RS485_RO,
    RS485_DI
  );

  Serial.println();
  Serial.println("=================================");
  Serial.println(" ESP32 + HW-097 + SN-3002");
  Serial.println("=================================");

  Serial.println("RS485 iniciado correctamente.");

  // ========================================================
  // WIFI
  // ========================================================

  conectarWiFi();
}


// ============================================================
// LOOP
// ============================================================

void loop()
{
  if (millis() - ultimaLectura >= INTERVALO)
  {
    ultimaLectura = millis();

    uint16_t datos[7];

    Serial.println();
    Serial.println("Consultando sensor...");

    // ======================================================
    // LEER LOS 7 REGISTROS DE UNA SOLA VEZ
    // ======================================================

    bool resultado = leerRegistros(
      0x0000,
      7,
      datos
    );

    if (resultado)
    {
      Serial.println("Lectura correcta.");

      mostrarDatos(datos);

      // ====================================================
      // ENVIAR A DJANGO
      // ====================================================

      enviarADjango(datos);
    }
    else
    {
      Serial.println("No se pudieron obtener los datos.");
    }
  }

  // ========================================================
  // RECONEXIÓN WIFI
  // ========================================================

  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi perdido. Intentando reconectar...");

    conectarWiFi();
  }
}





Codigo de conexio que es el que va a recibri desde el ardiono ide hecho en Python para Django:

1. views.py

En tu aplicación Django, por ejemplo sensor/views.py:

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def recibir_datos_sensor(request):

    # Solo aceptar peticiones POST
    if request.method != "POST":
        return JsonResponse({
            "error": "Solo se permiten peticiones POST"
        }, status=405)

    try:
        # Obtener el JSON enviado por el ESP32
        datos = json.loads(request.body)

        # Capturar los datos
        humedad = datos.get("humedad")
        temperatura = datos.get("temperatura")
        conductividad = datos.get("conductividad")
        ph = datos.get("ph")
        nitrogeno = datos.get("nitrogeno")
        fosforo = datos.get("fosforo")
        potasio = datos.get("potasio")

        # Mostrar los datos en la consola de Django
        print("====================================")
        print("      DATOS RECIBIDOS DEL SENSOR")
        print("====================================")
        print(f"Humedad:        {humedad}")
        print(f"Temperatura:    {temperatura}")
        print(f"Conductividad:  {conductividad}")
        print(f"pH:             {ph}")
        print(f"Nitrógeno:      {nitrogeno}")
        print(f"Fósforo:        {fosforo}")
        print(f"Potasio:        {potasio}")
        print("====================================")

        # Respuesta para el ESP32
        return JsonResponse({
            "estado": "ok",
            "mensaje": "Datos recibidos correctamente",
            "datos": datos
        })

    except json.JSONDecodeError:

        return JsonResponse({
            "estado": "error",
            "mensaje": "El JSON recibido no es válido"
        }, status=400)

    except Exception as e:

        return JsonResponse({
            "estado": "error",
            "mensaje": str(e)
        }, status=500)
2. urls.py

En el urls.py de tu aplicación:

from django.urls import path
from .views import recibir_datos_sensor


urlpatterns = [
    path(
        "api/lecturas/",
        recibir_datos_sensor,
        name="recibir_datos_sensor"
    ),
]

Y si tienes un urls.py principal del proyecto, debe incluir las URLs de tu aplicación:

from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("sensor.urls")),
]
3. Ahora coincide con el ESP32

En el código del ESP32 que te di anteriormente teníamos:

const char* DJANGO_URL =
    "http://192.168.1.100:8000/api/lecturas/";