# Documentación de Conexiones y Código del Sensor ESP32 — TierSystem

---

## 1. Conexiones Físicas del Hardware (ACTUALIZADO - Pines Libres de Error de Arranque)

Cada pin se conecta con su **cable individual directo** (sin empalmes ni puentes):

### A. Sonda SN-3002
* **Café** $\rightarrow$ +12V de la fuente o batería
* **Negro** $\rightarrow$ Negativo (−) de la fuente / GND común
* **Amarillo** $\rightarrow$ Borne **A** del HW-097
* **Azul** $\rightarrow$ Borne **B** del HW-097

### B. Módulo Convertidor HW-097 (MAX485)
* **VCC** $\rightarrow$ Pin **VIN** del ESP32 (5V)
* **GND** $\rightarrow$ Pin **GND** del ESP32
* **RO** $\rightarrow$ Pin **D16** del ESP32 *(RX2)*
* **DI** $\rightarrow$ Pin **D17** del ESP32 *(TX2)*
* **DE** $\rightarrow$ Pin **D4** del ESP32
* **RE** $\rightarrow$ Pin **D18** del ESP32
* **A** $\rightarrow$ Cable Amarillo de la sonda
* **B** $\rightarrow$ Cable Azul de la sonda

### C. ESP32 (NodeMCU Tipo-C)
* **D16** $\rightarrow$ RO del HW-097
* **D17** $\rightarrow$ DI del HW-097
* **D4** $\rightarrow$ DE del HW-097
* **D18** $\rightarrow$ RE del HW-097
* **VIN** $\rightarrow$ VCC del HW-097
* **GND** $\rightarrow$ GND del HW-097 y Negativo (−) de la fuente de 12V

---

## 2. CÓDIGO NUEVO Y ACTUALIZADO (Copiar este en Arduino IDE)

> **Cambio clave**: Pines corregidos a `RO:16`, `DI:17`, `DE:4`, `RE:18` para evitar el error `Wrong boot mode detected (0xb)` al subir código.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiMulti.h> // <-- Librería nativa para múltiples redes

// Instanciamos el objeto WiFiMulti
WiFiMulti wifiMulti;

// ============================================================
// CONFIGURACIÓN DJANGO
// ============================================================

// Esta es la IP actual de tu computadora en tu red local WiFi.
// Si en el futuro cambia, deberás actualizarla aquí.
// Ejemplo: http://192.168.100.78:8000/api/lecturas/
const char* DJANGO_URL = "http://10.3.249.123:8000/api/lecturas/";

// ============================================================
// PINES ESP32 + HW-097 (ACTUALIZADOS Y SEGUROS)
// ============================================================

#define RS485_RO 16  // RX2 - Cable a RO del HW-097
#define RS485_DI 17  // TX2 - Cable a DI del HW-097
#define RS485_DE 4   // Cable directo a DE del HW-097
#define RS485_RE 18  // Cable directo a RE del HW-097

// ============================================================
// UART DEL ESP32
// ============================================================

// UART2 por Hardware
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

  // Mínimo: ID + función + bytes + datos + CRC
  if (indice < 5)
  {
    Serial.println("ERROR: No se recibió respuesta del sensor.");
    return false;
  }

  // Comprobar ID
  if (respuesta[0] != SENSOR_ID)
  {
    Serial.println("ERROR: ID del sensor incorrecto.");
    return false;
  }

  // Comprobar Función
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

  // Extraer Registros
  for (uint16_t i = 0; i < cantidad; i++)
  {
    uint8_t posicion = 3 + (i * 2);

    datos[i] =
      ((uint16_t)respuesta[posicion] << 8) |
      respuesta[posicion + 1];
  }

  // Comprobar CRC
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

  Serial.print("Humedad:       "); Serial.println(datos[0]);
  Serial.print("Temperatura:   "); Serial.println(datos[1]);
  Serial.print("Conductividad: "); Serial.println(datos[2]);
  Serial.print("pH:            "); Serial.println(datos[3]);
  Serial.print("Nitrógeno (N): "); Serial.println(datos[4]);
  Serial.print("Fósforo (P):   "); Serial.println(datos[5]);
  Serial.print("Potasio (K):   "); Serial.println(datos[6]);

  Serial.println("=================================");
}

// ============================================================
// ENVIAR DATOS A DJANGO
// ============================================================

void enviarADjango(uint16_t *datos)
{
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi desconectado. No se envían datos.");
    return;
  }

  HTTPClient http;

  Serial.println();
  Serial.println("Enviando datos a Django...");

  http.begin(DJANGO_URL);
  http.addHeader("Content-Type", "application/json");

  // Armar JSON
  String json = "{";
  json += "\"humedad\":" + String(datos[0]) + ",";
  json += "\"temperatura\":" + String(datos[1]) + ",";
  json += "\"conductividad\":" + String(datos[2]) + ",";
  json += "\"ph\":" + String(datos[3]) + ",";
  json += "\"nitrogeno\":" + String(datos[4]) + ",";
  json += "\"fosforo\":" + String(datos[5]) + ",";
  json += "\"potasio\":" + String(datos[6]);
  json += "}";

  Serial.println("JSON enviado:");
  Serial.println(json);

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
// CONECTAR WIFI (MÚLTIPLES REDES)
// ============================================================

void conectarWiFiMulti()
{
  Serial.println();
  Serial.println("Iniciando WiFi Multi...");

  // Agrega tus redes WiFi aquí:
  wifiMulti.addAP("APRENDICES", "Apr3nd1z2025**");

  Serial.print("Conectando a la red con mejor señal");

  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("¡WiFi conectado exitosamente!");
  Serial.print("Conectado a la red: ");
  Serial.println(WiFi.SSID());
  Serial.print("IP del ESP32: ");
  Serial.println(WiFi.localIP());
}

// ============================================================
// SETUP
// ============================================================

void setup()
{
  Serial.begin(115200);

  // Configurar pines de control del HW-097 (D4 y D18)
  pinMode(RS485_DE, OUTPUT);
  pinMode(RS485_RE, OUTPUT);

  modoRecepcion();

  // UART RS485 en pines seguros (RX: D16, TX: D17)
  RS485Serial.begin(
    4800,
    SERIAL_8N1,
    RS485_RO, // D16
    RS485_DI  // D17
  );

  Serial.println();
  Serial.println("=================================");
  Serial.println(" ESP32 + HW-097 + SN-3002");
  Serial.println("=================================");
  Serial.println("RS485 iniciado correctamente en D16 (RX) y D17 (TX).");

  // Conectar a WiFi
  conectarWiFiMulti();
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

    bool resultado = leerRegistros(0x0000, 7, datos);

    if (resultado)
    {
      Serial.println("Lectura correcta.");
      mostrarDatos(datos);
      enviarADjango(datos);
    }
    else
    {
      Serial.println("No se pudieron obtener los datos.");
    }
  }

  // Reconexión WiFi automática si se pierde
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi perdido. Intentando reconectar...");
    wifiMulti.run();
  }
}
```

---

## 3. CÓDIGO ANTERIOR (RESPALDO / BACKUP)

<details>
<summary><b>Click aquí para ver el código anterior de respaldo (Pines antiguos D2, D15, D13, D5)</b></summary>

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiMulti.h> // <-- Librería nativa para múltiples redes

// Instanciamos el objeto WiFiMulti
WiFiMulti wifiMulti;

// ============================================================
// CONFIGURACIÓN DJANGO
// ============================================================

const char* DJANGO_URL = "http://10.3.249.123:8000/api/lecturas/";

// ============================================================
// PINES ESP32 + HW-097 (ANTIGUOS)
// ============================================================

#define RS485_DI 2
#define RS485_DE 15
#define RS485_RE 13
#define RS485_RO 5

// ============================================================
// UART DEL ESP32
// ============================================================

HardwareSerial RS485Serial(2);

#define SENSOR_ID 1
const unsigned long INTERVALO = 5000;
unsigned long ultimaLectura = 0;

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

  while (RS485Serial.available())
  {
    RS485Serial.read();
  }

  modoTransmision();
  delay(2);

  RS485Serial.write(solicitud, 8);
  RS485Serial.flush();
  delay(2);

  modoRecepcion();

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

  if (indice < 5)
  {
    Serial.println("ERROR: No se recibió respuesta del sensor.");
    return false;
  }

  if (respuesta[0] != SENSOR_ID)
  {
    Serial.println("ERROR: ID del sensor incorrecto.");
    return false;
  }

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

  for (uint16_t i = 0; i < cantidad; i++)
  {
    uint8_t posicion = 3 + (i * 2);

    datos[i] =
      ((uint16_t)respuesta[posicion] << 8) |
      respuesta[posicion + 1];
  }

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

void mostrarDatos(uint16_t *datos)
{
  Serial.println();
  Serial.println("=================================");
  Serial.println("      DATOS DEL SENSOR");
  Serial.println("=================================");

  Serial.print("Registro 0: "); Serial.println(datos[0]);
  Serial.print("Registro 1: "); Serial.println(datos[1]);
  Serial.print("Registro 2: "); Serial.println(datos[2]);
  Serial.print("Registro 3: "); Serial.println(datos[3]);
  Serial.print("Registro 4: "); Serial.println(datos[4]);
  Serial.print("Registro 5: "); Serial.println(datos[5]);
  Serial.print("Registro 6: "); Serial.println(datos[6]);

  Serial.println("=================================");
}

void enviarADjango(uint16_t *datos)
{
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi desconectado. No se envían datos.");
    return;
  }

  HTTPClient http;

  Serial.println();
  Serial.println("Enviando datos a Django...");

  http.begin(DJANGO_URL);
  http.addHeader("Content-Type", "application/json");

  String json = "{";
  json += "\"humedad\":" + String(datos[0]) + ",";
  json += "\"temperatura\":" + String(datos[1]) + ",";
  json += "\"conductividad\":" + String(datos[2]) + ",";
  json += "\"ph\":" + String(datos[3]) + ",";
  json += "\"nitrogeno\":" + String(datos[4]) + ",";
  json += "\"fosforo\":" + String(datos[5]) + ",";
  json += "\"potasio\":" + String(datos[6]);
  json += "}";

  Serial.println("JSON enviado:");
  Serial.println(json);

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

void conectarWiFiMulti()
{
  Serial.println();
  Serial.println("Iniciando WiFi Multi...");

  wifiMulti.addAP("APRENDICES", "Apr3nd1z2025**");

  Serial.print("Conectando a la red con mejor señal");

  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("¡WiFi conectado exitosamente!");
  Serial.print("Conectado a la red: ");
  Serial.println(WiFi.SSID());
  Serial.print("IP del ESP32: ");
  Serial.println(WiFi.localIP());
}

void setup()
{
  Serial.begin(115200);

  pinMode(RS485_DE, OUTPUT);
  pinMode(RS485_RE, OUTPUT);

  modoRecepcion();

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

  conectarWiFiMulti();
}

void loop()
{
  if (millis() - ultimaLectura >= INTERVALO)
  {
    ultimaLectura = millis();

    uint16_t datos[7];

    Serial.println();
    Serial.println("Consultando sensor...");

    bool resultado = leerRegistros(0x0000, 7, datos);

    if (resultado)
    {
      Serial.println("Lectura correcta.");
      mostrarDatos(datos);
      enviarADjango(datos);
    }
    else
    {
      Serial.println("No se pudieron obtener los datos.");
    }
  }

  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi perdido. Intentando reconectar...");
    wifiMulti.run();
  }
}
```
</details>

---

## 4. Código Backend Django de Recepción (`api/lecturas/`)

### En `apps/sensores/views.py`:
```python
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def recibir_datos_sensor(request):
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permiten peticiones POST"}, status=405)

    try:
        datos = json.loads(request.body)
        humedad = datos.get("humedad")
        temperatura = datos.get("temperatura")
        conductividad = datos.get("conductividad")
        ph = datos.get("ph")
        nitrogeno = datos.get("nitrogeno")
        fosforo = datos.get("fosforo")
        potasio = datos.get("potasio")

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

        return JsonResponse({
            "estado": "ok",
            "mensaje": "Datos recibidos correctamente",
            "datos": datos
        })

    except json.JSONDecodeError:
        return JsonResponse({"estado": "error", "mensaje": "El JSON recibido no es válido"}, status=400)
    except Exception as e:
        return JsonResponse({"estado": "error", "mensaje": str(e)}, status=500)
```