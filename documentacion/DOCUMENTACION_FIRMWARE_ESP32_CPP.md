# Documentación Técnica del Firmware C++ para ESP32 — Sensor Edafológico IoT TierSystem

> **Subsistema de Captura y Telemetría en Campo: Microcontrolador ESP32 + Transceptor RS485 (HW-097) + Sonda Industrial NPK 7 en 1 (SN-3002).**
> 
> *Manual de Arquitectura Electrónica, Protocolo Modbus RTU, Algoritmo CRC-16 y Explicación Detallada del Código C++.*

---

## Tabla de Contenido

1. [Visión General del Subsistema de Hardware](#1-visión-general-del-subsistema-de-hardware)
2. [Arquitectura Electrónica y Conexiones Físicas](#2-arquitectura-electrónica-y-conexiones-físicas)
   - 2.1 Componentes del Sistema
   - 2.2 Diagrama de Conexiones Pin a Pin
   - 2.3 Solución al Error Crítico de Arranque `Wrong boot mode detected (0xb)`
3. [Protocolo Industrial Modbus RTU sobre Bus RS485](#3-protocolo-industrial-modbus-rtu-sobre-bus-rs485)
   - 3.1 Fundamentos de la Señal Diferencial Balanceada (RS485)
   - 3.2 Operación Half-Duplex y Control de Flujo (Pines DE y RE)
   - 3.3 Estructura de la Trama de Consulta (Master Request)
   - 3.4 Estructura de la Trama de Respuesta (Slave Response)
4. [El Algoritmo Matemático de Redundancia Cíclica: CRC-16 (Modbus)](#4-el-algoritmo-matemático-de-redundancia-cíclica-crc-16-modbus)
   - 4.1 Principio Matemático y Polinomio Generador `0xA001`
   - 4.2 Desglose Bit a Bit del Cálculo
5. [Código Fuente Completo en C++ (Arduino IDE / PlatformIO)](#5-código-fuente-completo-en-c-arduino-ide--platformio)
6. [Explicación Minuciosa y Traducción Línea por Línea del Código](#6-explicación-minuciosa-y-traducción-línea-por-línea-del-código)
   - 6.1 Directivas de Preprocesador y Librerías del Sistema
   - 6.2 Definición de Pines Seguros y Constantes
   - 6.3 Inicialización del Puerto Serie por Hardware UART2
   - 6.4 Funciones de Conmutación de Bus (`modoTransmision` y `modoRecepcion`)
   - 6.5 Función de Cálculo de Integridad `calcularCRC`
   - 6.6 Función de Consulta y Parseo `leerRegistros`
   - 6.7 Función de Serialización y Despacho HTTP `enviarADjango`
   - 6.8 Gestión Multi-Red y Reconexión Automática `conectarWiFiMulti`
   - 6.9 Rutinas de Ciclo de Vida: `setup()` y `loop()`
7. [Integración con el Servidor Django: Del Byte al ORM](#7-integración-con-el-servidor-django-del-byte-al-orm)
   - 7.1 Mapeo de Registros Modbus a Parámetros Edafológicos
   - 7.2 Justificación del Desescalado Decimal (`/ 10.0`)
   - 7.3 Interacción con el Filtro Anti-Ruido Digital (Moda y Mediana)
8. [Guía de Diagnóstico y Resolución de Problemas (Troubleshooting)](#8-guía-de-diagnóstico-y-resolución-de-problemas-troubleshooting)

---

## 1. Visión General del Subsistema de Hardware

En el ecosistema **TierSystem**, el microcontrolador **ESP32** actúa como el nodo inteligente de borde (*Edge Computing*). Su función principal es cerrar la brecha entre el mundo analógico/físico de la finca y el sistema web en la nube o servidor local:

1. **Interroga a la sonda física de suelo** mediante el estándar industrial de automatización **Modbus RTU** sobre una interfaz física **RS485**.
2. **Adquiere las 7 magnitudes agronómicas fundamentales**: Humedad volumétrica, Temperatura edáfica, Conductividad eléctrica (salinidad), Potencial de hidrógeno (pH), Nitrógeno (N), Fósforo (P) y Potasio (K).
3. **Verifica la integridad criptográfica/matemática** de los datos leídos mediante un algoritmo de comprobación de redundancia cíclica (**CRC-16**).
4. **Empaqueta las lecturas brutas en formato JSON** (`JavaScript Object Notation`).
5. **Transmite la telemetría en tiempo real** hacia los controladores REST del backend de Django a través de una conexión inalámbrica **WiFi** mediante peticiones HTTP seguras.

```
 ┌──────────────────────┐             ┌─────────────────────┐
 │  Sonda Edafológica   │             │ Módulo Transceptor  │
 │  Industrial SN-3002  │  Líneas A/B │   HW-097 (MAX485)   │
 │   (7 en 1 - Suelo)   ├─────────────┤                     │
 └──────────┬───────────┘    RS485    └──────────┬──────────┘
            │ 12V DC                             │ Niveles TTL (3.3V / 5V)
            │                                    │ UART2 (RX2/TX2) + DE/RE
            │                                    ▼
            │                         ┌─────────────────────┐
            │                         │   ESP32 NodeMCU     │
            │                         │  (Controlador C++)  │
            │                         └──────────┬──────────┘
            │                                    │
            │                                    │ WiFi 802.11 b/g/n
            │                                    │ HTTP POST (Payload JSON)
            │                                    ▼
 ┌──────────┴───────────┐             ┌─────────────────────┐
 │ Batería / Fuente 12V │             │   Servidor Django   │
 │ (Negativo Común GND) ├─────────────┤ /api/lecturas/      │
 └──────────────────────┘             └─────────────────────┘
```

---

## 2. Arquitectura Electrónica y Conexiones Físicas

### 2.1 Componentes del Sistema

1. **Microcontrolador ESP32 NodeMCU (30 pines / USB Tipo-C)**:
   - Procesador Tensilica Xtensa Dual-Core de 32 bits a 240 MHz.
   - Módulo de radiofrecuencia integrado WiFi 802.11 b/g/n (2.4 GHz) y Bluetooth 4.2 BLE.
   - Múltiples puertos UART por hardware (UART0, UART1, UART2).
2. **Módulo Transceptor HW-097 (Basado en el circuito integrado MAX485)**:
   - Convierte los niveles lógicos serie TTL (0V - 3.3V/5V) del microcontrolador en señales diferenciales de voltaje RS485 para comunicaciones industriales de larga distancia y alta inmunidad al ruido.
3. **Sonda de Suelo Industrial 7 en 1 (Modelo SN-3002)**:
   - Fabricada con electrodos de acero inoxidable grado 316 resistentes a la corrosión por fertilizantes y humedad.
   - Requiere una alimentación eléctrica industrial de **12V a 24V DC**.
   - Comunicación nativa: Esclavo Modbus RTU con dirección por defecto `0x01` a **4800 baudios (8N1)**.
4. **Alimentación Eléctrica Portátil de Campo**:
   - Batería recargable Li-Ion / LiFePO4 de 12V DC para energizar la sonda.
   - Regulador o conexión USB directa para alimentar el ESP32.

---

### 2.2 Diagrama de Conexiones Pin a Pin

Para garantizar una señal eléctrica limpia y estable en campo, cada cable debe conectarse de forma independiente y directa:

#### A. Cableado de la Sonda SN-3002
| Color de Cable | Conexión Física | Descripción |
| :--- | :--- | :--- |
| **Café (Marrón)** | **+12V DC** | Positivo de la batería o fuente de poder industrial. |
| **Negro** | **GND / Negativo (−)** | Negativo de la fuente de 12V (**Masa común con el ESP32**). |
| **Amarillo** | **Borne A del HW-097** | Línea de datos diferencial no inversora (+). |
| **Azul** | **Borne B del HW-097** | Línea de datos diferencial inversora (−). |

#### B. Cableado del Módulo Transceptor HW-097 (MAX485) hacia el ESP32
| Pin del HW-097 | Pin del ESP32 | Función Electrónica |
| :--- | :--- | :--- |
| **VCC** | **VIN (5V)** | Alimentación del circuito integrado MAX485. |
| **GND** | **GND** | Tierra común de referencia con el ESP32 y la batería de 12V. |
| **RO** (*Receiver Output*) | **D16 (GPIO16)** | Salida de recepción de datos hacia el pin **RX2** del UART2. |
| **DI** (*Driver Input*) | **D17 (GPIO17)** | Entrada de transmisión de datos desde el pin **TX2** del UART2. |
| **DE** (*Driver Enable*) | **D4 (GPIO4)** | Habilitador del transmisor (Activo en nivel ALTO / 3.3V). |
| **RE** (*Receiver Enable*) | **D18 (GPIO18)** | Habilitador del receptor (Activo en nivel BAJO / 0V). |
| **A** | Cable Amarillo | Conexión con la sonda industrial. |
| **B** | Cable Azul | Conexión con la sonda industrial. |

---

### 2.3 Solución al Error Crítico de Arranque `Wrong boot mode detected (0xb)`

Uno de los errores más frustrantes al trabajar con el ESP32 y módulos RS485 en Arduino IDE es el siguiente volcado por consola al reiniciar o subir el código:

```text
rst:0x10 (RTCWDT_RTC_RESET),boot:0xb (SPI_FAST_FLASH_BOOT)
flash read err, 1000
ets_main.c 371
ets Jun  8 2016 00:22:57
Wrong boot mode detected (0xb)!
The chip was prevented from booting, or the flash is corrupted.
```

#### Causa Raíz del Problema: Los Pines de Strapping
El microcontrolador ESP32 utiliza ciertos pines GPIO para leer su estado lógico (**ALTO** o **BAJO**) en el microsegundo exacto en que se enciende o se resetea. Estos pines se denominan **Pines de Configuración de Arranque (Strapping Pins)**:
- **GPIO2**: Debe estar en BAJO durante el arranque para ingresar en modo de descarga de flash.
- **GPIO12 (MTDI)**: Si se fuerza a nivel ALTO durante el encendido, conmuta el voltaje interno de la memoria Flash SPI de 3.3V a 1.8V, impidiendo que el chip lea su propio programa.
- **GPIO15 (MTDO)**: Controla la salida de mensajes de depuración del cargador de arranque ROM.

En diseños antiguos, se conectaban los pines `DE` y `RE` a los pines **D2, D12 o D15**. Cuando el módulo MAX485 recibía corriente, sus resistencias pull-up internas forzaban voltajes parásitos en estos pines durante el encendido, engañando al chip ESP32 sobre su modo de arranque y provocando el bloqueo total del procesador (`boot: 0xb`).

#### Solución Implementada en TierSystem
Se migraron todos los pines de control serie y habilitación hacia **GPIOs de propósito general 100% seguros**:
- Se seleccionaron los pines **D16 (GPIO16)** y **D17 (GPIO17)** para la comunicación serie porque están directamente conectados al periférico de silicio **UART2 por Hardware** y no intervienen en la secuencia de arranque.
- Se seleccionaron los pines **D4 (GPIO4)** y **D18 (GPIO18)** para controlar `DE` y `RE` porque son pines neutros que no interfieren en el ciclo de inicio del sistema operativo interno.

---

## 3. Protocolo Industrial Modbus RTU sobre Bus RS485

### 3.1 Fundamentos de la Señal Diferencial Balanceada (RS485)

A diferencia de las comunicaciones UART tradicionales o I2C (que miden el voltaje respecto a una masa común y son muy susceptibles a interferencias electromagnéticas generadas por motores o tormentas en el campo), el bus **RS485** utiliza una **señal diferencial balanceada** compuesta por dos cables trenzados: **Línea A** y **Línea B**.

- **Bit Lógico '1' (Marca / Reposo)**: $V_A - V_B > +200\text{ mV}$
- **Bit Lógico '0' (Espacio)**: $V_A - V_B < -200\text{ mV}$

Cualquier interferencia electromagnética que impacte el cableado de la finca afectará por igual a las dos líneas (ruido de modo común). Como el receptor MAX485 únicamente amplifica la **diferencia de potencial** entre ambas líneas, el ruido se anula matemáticamente, permitiendo tender cables de hasta 100 metros sin pérdida de datos.

### 3.2 Operación Half-Duplex y Control de Flujo (Pines DE y RE)

El estándar RS485 es **Half-Duplex**: los dispositivos pueden transmitir o recibir información, pero no ambas cosas de forma simultánea, ya que comparten el mismo par de cables A y B. El circuito integrado MAX485 cuenta con dos pines de control:

- **DE (Driver Enable)**: Controla la etapa de salida (transmisor).
  - `HIGH (3.3V)`: Activa los transmisores y acopla la señal del ESP32 hacia el bus RS485.
  - `LOW (0V)`: Desactiva los transmisores y pone las salidas en alta impedancia (desconectado).
- **\RE (Receiver Enable - Lógica Invertida)**: Controla la etapa de entrada (receptor).
  - `LOW (0V)`: Habilita el receptor; las señales del bus RS485 pasan al pin `RO` del ESP32.
  - `HIGH (3.3V)`: Desactiva el receptor.

#### Estados de Conmutación en el Firmware
1. **Modo Transmisión**: `DE = HIGH`, `RE = HIGH`. El ESP32 habla hacia la sonda; su propio receptor se apaga para no escuchar su propio eco.
2. **Modo Recepción**: `DE = LOW`, `RE = LOW`. El ESP32 se calla y pone sus oídos en el bus a la espera de los bytes emitidos por la sonda.

---

### 3.3 Estructura de la Trama de Consulta (Master Request)

Para solicitar las lecturas a la sonda de suelo, el ESP32 (Maestro) envía un paquete binario estricto de **8 bytes**:

| Byte # | Campo | Valor Hex | Significado Técnico |
| :---: | :--- | :---: | :--- |
| **0** | **ID del Esclavo** | `0x01` | Dirección asignada a la sonda de suelo en el bus. |
| **1** | **Código de Función**| `0x03` | *Read Holding Registers* (Lectura de registros de retención de 16 bits). |
| **2** | **Registro Inicial (High)**| `0x00` | Byte alto de la dirección de memoria inicial (`0x0000`). |
| **3** | **Registro Inicial (Low)** | `0x00` | Byte bajo de la dirección de memoria inicial (`0x0000`). |
| **4** | **Cantidad Registros (High)**| `0x00` | Byte alto del total de variables solicitadas. |
| **5** | **Cantidad Registros (Low)** | `0x07` | Byte bajo: Solicitamos exactamente **7 registros consecutivos**. |
| **6** | **CRC16 (Low Byte)** | `0x04` | Byte bajo de la suma de redundancia cíclica calculada. |
| **7** | **CRC16 (High Byte)** | `0x08` | Byte alto de la suma de redundancia cíclica calculada. |

---

### 3.4 Estructura de la Trama de Respuesta (Slave Response)

Cuando la sonda SN-3002 recibe el paquete anterior y valida el CRC16, responde con un paquete binario de **19 bytes**:

| Byte # | Parámetro que Contiene | Representación en C++ |
| :---: | :--- | :--- |
| **0** | **ID del Sensor** (`0x01`) | Debe coincidir con `SENSOR_ID`. |
| **1** | **Función Confirmada** (`0x03`) | Confirma que se ejecutó la lectura de registros. |
| **2** | **Conteo de Bytes de Datos** (`0x0E`) | 14 bytes de datos ($7 \text{ registros} \times 2 \text{ bytes}$). |
| **3 - 4** | **Registro 0: Humedad de Suelo** | Entero 16 bits sin signo (ej. `0x02AD` = 685 $\rightarrow$ 68.5%). |
| **5 - 6** | **Registro 1: Temperatura Edáfica** | Entero 16 bits sin signo (ej. `0x00F2` = 242 $\rightarrow$ 24.2 °C). |
| **7 - 8** | **Registro 2: Conductividad Eléctrica**| Entero 16 bits sin signo (ej. `0x04B0` = 1200 µS/cm). |
| **9 - 10**| **Registro 3: Potencial de Hidrógeno (pH)**| Entero 16 bits sin signo (ej. `0x003E` = 62 $\rightarrow$ pH 6.2). |
| **11 - 12**| **Registro 4: Nitrógeno Disponible (N)**| Entero 16 bits sin signo (mg/kg o ppm). |
| **13 - 14**| **Registro 5: Fósforo Disponible (P)** | Entero 16 bits sin signo (mg/kg o ppm). |
| **15 - 16**| **Registro 6: Potasio Intercambiable (K)**| Entero 16 bits sin signo (mg/kg o ppm). |
| **17** | **CRC16 Recibido (Low Byte)** | Byte bajo del código de verificación emitido por la sonda. |
| **18** | **CRC16 Recibido (High Byte)** | Byte alto del código de verificación emitido por la sonda. |

---

## 4. El Algoritmo Matemático de Redundancia Cíclica: CRC-16 (Modbus)

### 4.1 Principio Matemático y Polinomio Generador `0xA001`

En entornos agrícolas, el encendido de motobombas, generadores a gasolina o cables de alta tensión induce ruidos en la señal serie. Para evitar que un byte corrupto sea interpretado erróneamente como un valor químico válido, Modbus utiliza el algoritmo **CRC-16** estándar.

- El cálculo se basa en la división polinómica en el cuerpo de Galois $GF(2)$.
- Se utiliza el polinomio estándar invertido para Modbus: **`0xA001`** (representación reflejada del polinomio algebraico $x^{16} + x^{15} + x^2 + 1$).
- El registro de cálculo se inicializa con todos sus bits en uno: **`0xFFFF`**.

### 4.2 Desglose Bit a Bit del Cálculo

A continuación se muestra la función exacta en C++ implementada en el firmware:

```cpp
uint16_t calcularCRC(uint8_t *buffer, uint8_t longitud)
{
  uint16_t crc = 0xFFFF; // 1. Inicializar registro en 16 unos

  for (uint8_t pos = 0; pos < longitud; pos++)
  {
    crc ^= (uint16_t)buffer[pos]; // 2. XOR bit a bit con el byte de datos actual

    for (uint8_t i = 8; i != 0; i--) // 3. Procesar los 8 bits
    {
      if ((crc & 0x0001) != 0) // Si el bit menos significativo es 1
      {
        crc >>= 1;            // Desplazar a la derecha 1 bit
        crc ^= 0xA001;        // Aplicar máscara XOR con el polinomio Modbus
      }
      else                    // Si el bit menos significativo es 0
      {
        crc >>= 1;            // Simplemente desplazar a la derecha
      }
    }
  }

  return crc; // 4. Retorna el código de comprobación de 16 bits
}
```

#### ¿Por qué el orden de los bytes de CRC se invierte?
En el estándar Modbus RTU, el resultado del CRC se transmite en formato **Little-Endian**: primero se coloca el byte menos significativo (*Low Byte*) y posteriormente el byte más significativo (*High Byte*).

---

## 5. Código Fuente Completo en C++ (Arduino IDE / PlatformIO)

Este es el firmware oficial y completo de producción utilizado en TierSystem:

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiMulti.h> // Gestión robusta de múltiples puntos de acceso WiFi

// Instanciación del administrador de conexiones múltiples
WiFiMulti wifiMulti;

// ============================================================
// CONFIGURACIÓN DEL SERVIDOR DJANGO
// ============================================================

// Dirección IP local y puerto donde escucha el servidor Django
// Endpoint oficial del backend: POST /api/lecturas/
const char* DJANGO_URL = "http://10.3.249.123:8000/api/lecturas/";

// ============================================================
// ASIGNACIÓN DE PINES SEGUROS (ESP32 + HW-097 / MAX485)
// ============================================================

#define RS485_RO 16  // Pin RX2 por Hardware del ESP32 -> Cable al pin RO del MAX485
#define RS485_DI 17  // Pin TX2 por Hardware del ESP32 -> Cable al pin DI del MAX485
#define RS485_DE 4   // GPIO4 -> Habilitador de Transmisión del MAX485
#define RS485_RE 18  // GPIO18 -> Habilitador de Recepción del MAX485

// ============================================================
// PUERTO SERIE POR HARDWARE (UART2)
// ============================================================

// Instancia el puerto serie 2 nativo del silicio del ESP32
HardwareSerial RS485Serial(2);

// ============================================================
// PARÁMETROS DEL PROTOCOLO MODBUS
// ============================================================

#define SENSOR_ID 1  // Dirección física esclava de la sonda de suelo

// ============================================================
// TEMPORIZACIÓN NO BLOQUEANTE
// ============================================================

const unsigned long INTERVALO = 5000; // Cadencia de muestreo: 5000 ms (5 segundos)
unsigned long ultimaLectura = 0;       // Almacena la estampa de tiempo anterior (millis)

// ============================================================
// GESTIÓN DEL SENTIDO DEL BUS RS485 (HALF-DUPLEX)
// ============================================================

void modoTransmision()
{
  digitalWrite(RS485_DE, HIGH); // Habilita el transmisor
  digitalWrite(RS485_RE, HIGH); // Deshabilita el receptor (evita auto-eco)
}

void modoRecepcion()
{
  digitalWrite(RS485_DE, LOW);  // Deshabilita el transmisor
  digitalWrite(RS485_RE, LOW);  // Habilita el receptor para escuchar la respuesta
}

// ============================================================
// CÁLCULO DE REDUNDANCIA CÍCLICA CRC-16 (POLINOMIO 0xA001)
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
// CONSULTA Y PARSEO DE REGISTROS MODBUS RTU
// ============================================================

bool leerRegistros(uint16_t registroInicial,
                   uint16_t cantidad,
                   uint16_t *datos)
{
  uint8_t solicitud[8];

  // Construcción de la trama de petición
  solicitud[0] = SENSOR_ID;
  solicitud[1] = 0x03; // Función 03: Read Holding Registers
  solicitud[2] = highByte(registroInicial);
  solicitud[3] = lowByte(registroInicial);
  solicitud[4] = highByte(cantidad);
  solicitud[5] = lowByte(cantidad);

  // Cálculo de verificación de la solicitud
  uint16_t crc = calcularCRC(solicitud, 6);
  solicitud[6] = lowByte(crc);
  solicitud[7] = highByte(crc);

  // Limpiar cualquier byte residual en el búfer de entrada
  while (RS485Serial.available())
  {
    RS485Serial.read();
  }

  // Conmutar a modo transmisión y enviar paquete por el bus
  modoTransmision();
  delay(2); // Pequeña pausa de estabilización de nivel eléctrico

  RS485Serial.write(solicitud, 8);
  RS485Serial.flush(); // Espera obligatoria hasta vaciar el búfer de transmisión UART
  delay(2);

  // Conmutar inmediatamente a modo recepción
  modoRecepcion();

  // Recepción de la respuesta con ventana de timeout de 1000 ms
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
        break; // Prevenir desbordamiento de búfer
      }
    }
  }

  // 1. Validar longitud mínima del paquete (ID + Función + Bytes + Datos + CRC)
  if (indice < 5)
  {
    Serial.println("ERROR: No se recibió respuesta de la sonda (Timeout).");
    return false;
  }

  // 2. Validar que la respuesta provenga de la sonda interrogada
  if (respuesta[0] != SENSOR_ID)
  {
    Serial.println("ERROR: El ID de la respuesta no coincide.");
    return false;
  }

  // 3. Validar código de función de retorno
  if (respuesta[1] != 0x03)
  {
    Serial.println("ERROR: Código de función Modbus erróneo o código de excepción.");
    return false;
  }

  // 4. Validar que el conteo de bytes coincida con los registros pedidos (7 * 2 = 14 bytes)
  uint8_t bytesDatos = respuesta[2];
  if (bytesDatos != cantidad * 2)
  {
    Serial.println("ERROR: Discrepancia en el conteo de bytes de datos recibidos.");
    return false;
  }

  // 5. Reconstrucción de registros de 16 bits (Big-Endian: Byte Alto primero)
  for (uint16_t i = 0; i < cantidad; i++)
  {
    uint8_t posicion = 3 + (i * 2);
    datos[i] = ((uint16_t)respuesta[posicion] << 8) | respuesta[posicion + 1];
  }

  // 6. Validación matemática del CRC16 recibido
  uint16_t crcRecibido = respuesta[indice - 2] | ((uint16_t)respuesta[indice - 1] << 8);
  uint16_t crcCalculado = calcularCRC(respuesta, indice - 2);

  if (crcRecibido != crcCalculado)
  {
    Serial.println("ERROR: Fallo de verificación CRC (Trama de datos corrupta).");
    return false;
  }

  return true; // Trama perfecta y validada
}

// ============================================================
// IMPRESIÓN POR MONITOR SERIE (DEPURACIÓN LOCAL)
// ============================================================

void mostrarDatos(uint16_t *datos)
{
  Serial.println();
  Serial.println("=========================================");
  Serial.println("   DATOS BRUTOS CAPTURADOS DE LA SONDA   ");
  Serial.println("=========================================");
  Serial.print("Humedad Bruta:       "); Serial.println(datos[0]);
  Serial.print("Temperatura Bruta:   "); Serial.println(datos[1]);
  Serial.print("Conductividad (CE):  "); Serial.println(datos[2]);
  Serial.print("pH Bruto:            "); Serial.println(datos[3]);
  Serial.print("Nitrógeno (N):       "); Serial.println(datos[4]);
  Serial.print("Fósforo (P):         "); Serial.println(datos[5]);
  Serial.print("Potasio (K):         "); Serial.println(datos[6]);
  Serial.println("=========================================");
}

// ============================================================
// ENVÍO DE TELEMETRÍA POR HTTP POST HACIA DJANGO
// ============================================================

void enviarADjango(uint16_t *datos)
{
  // Comprobar estado de conexión del enlace de radio
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("WiFi desconectado. Omitiendo despacho a Django.");
    return;
  }

  HTTPClient http;

  Serial.println();
  Serial.println("Enviando paquete JSON hacia Django...");

  // Inicializar cliente HTTP apuntando a la URL del backend
  http.begin(DJANGO_URL);
  http.addHeader("Content-Type", "application/json");

  // Serialización manual eficiente del objeto JSON
  String json = "{";
  json += "\"humedad\":" + String(datos[0]) + ",";
  json += "\"temperatura\":" + String(datos[1]) + ",";
  json += "\"conductividad\":" + String(datos[2]) + ",";
  json += "\"ph\":" + String(datos[3]) + ",";
  json += "\"nitrogeno\":" + String(datos[4]) + ",";
  json += "\"fosforo\":" + String(datos[5]) + ",";
  json += "\"potasio\":" + String(datos[6]);
  json += "}";

  Serial.println("Payload JSON:");
  Serial.println(json);

  // Ejecución de la petición POST
  int codigoRespuesta = http.POST(json);

  Serial.print("Código de Estado HTTP: ");
  Serial.println(codigoRespuesta);

  if (codigoRespuesta > 0)
  {
    String respuestaServidor = http.getString();
    Serial.println("Respuesta del Backend Django:");
    Serial.println(respuestaServidor);
  }
  else
  {
    Serial.print("Fallo en la petición HTTP: ");
    Serial.println(http.errorToString(codigoRespuesta));
  }

  http.end(); // Liberación de recursos y cierre de socket TCP
}

// ============================================================
// ADMINISTRADOR MULTI-WIFI
// ============================================================

void conectarWiFiMulti()
{
  Serial.println();
  Serial.println("Iniciando conexión con WiFiMulti...");

  // Registro de redes conocidas (agrega aquí el punto de acceso móvil o de finca)
  wifiMulti.addAP("APRENDICES", "Apr3nd1z2025**");
  wifiMulti.addAP("TIERSYSTEM_CAMPO", "CampoSeguro2026");

  Serial.print("Buscando y negociando con la red de mayor potencia RSSI");

  // Espera activa hasta establecer conexión exitosa
  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("¡Enlace WiFi establecido exitosamente!");
  Serial.print("SSID Conectado: "); Serial.println(WiFi.SSID());
  Serial.print("Dirección IP asignada al ESP32: "); Serial.println(WiFi.localIP());
}

// ============================================================
// CONFIGURACIÓN INICIAL (SETUP)
// ============================================================

void setup()
{
  // Puerto serie de depuración hacia el computador (USB)
  Serial.begin(115200);

  // Configuración de los pines de conmutación del MAX485
  pinMode(RS485_DE, OUTPUT);
  pinMode(RS485_RE, OUTPUT);

  // Estado inicial de reposo: escucha del bus
  modoRecepcion();

  // Inicialización de la UART2 física en pines seguros (4800 baudios, 8 bits de datos, sin paridad, 1 bit de parada)
  RS485Serial.begin(
    4800,
    SERIAL_8N1,
    RS485_RO, // Pin D16 (RX2)
    RS485_DI  // Pin D17 (TX2)
  );

  Serial.println();
  Serial.println("=========================================");
  Serial.println(" FIRMWARE ESP32 INICIALIZADO - TIERSYSTEM");
  Serial.println("=========================================");
  Serial.println("UART2 activa a 4800 bps en D16 (RX) y D17 (TX).");

  // Conexión inicial al entorno de red
  conectarWiFiMulti();
}

// ============================================================
// BUCLE PRINCIPAL DE EJECUCIÓN (LOOP)
// ============================================================

void loop()
{
  // Verificación del temporizador no bloqueante (cada 5 segundos)
  if (millis() - ultimaLectura >= INTERVALO)
  {
    ultimaLectura = millis();

    uint16_t datos[7];

    Serial.println();
    Serial.println("Consultando sonda edafológica...");

    // Solicita 7 registros consecutivos a partir de la dirección 0x0000
    bool exito = leerRegistros(0x0000, 7, datos);

    if (exito)
    {
      Serial.println("Lectura exitosa.");
      mostrarDatos(datos);      // Imprime en el monitor serie
      enviarADjango(datos);     // Despacha los datos por HTTP hacia el servidor
    }
    else
    {
      Serial.println("Fallo al interrogar la sonda de suelo.");
    }
  }

  // Supervisión y reconexión automática de la conexión WiFi
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("Enlace WiFi interrumpido. Reintentando asociación...");
    wifiMulti.run();
  }
}
```

---

## 6. Explicación Minuciosa y Traducción Línea por Línea del Código

A continuación se traduce y explica qué hace cada bloque de instrucciones en el procesador del microcontrolador:

### 6.1 Directivas de Preprocesador y Librerías del Sistema

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiMulti.h>
```
- `#include <WiFi.h>`: Proporciona las funciones de bajo nivel para controlar el chip de radiofrecuencia del ESP32, gestionar direcciones MAC y configurar modos de red (Station o Access Point).
- `#include <HTTPClient.h>`: Implementa un cliente web completo que permite al ESP32 actuar como un navegador: abrir sockets TCP, estructurar cabeceras HTTP (`User-Agent`, `Content-Type`) y ejecutar peticiones `GET` y `POST`.
- `#include <WiFiMulti.h>`: Clase nativa avanzada del framework de Espressif. A diferencia de `WiFi.begin()`, que solo conoce una red fija, `WiFiMulti` permite registrar múltiples credenciales WiFi (ej. la red del laboratorio del SENA, la zona WiFi compartida del teléfono celular del laboratorista en la finca, etc.). La librería escanea el espectro electromagnético y se asocia automáticamente a la red disponible que tenga la mayor potencia de señal (**RSSI**).

---

### 6.2 Definición de Pines Seguros y Constantes

```cpp
const char* DJANGO_URL = "http://10.3.249.123:8000/api/lecturas/";
#define RS485_RO 16
#define RS485_DI 17
#define RS485_DE 4
#define RS485_RE 18
```
- `DJANGO_URL`: Cadena constante con la dirección IP y puerto del servidor Django en la red de área local donde corre el endpoint receptor de telemetría.
- `#define RS485_RO 16`: Define que el cable proveniente de la patilla **RO** (*Receiver Output*) del MAX485 ingresa por el pin físico **D16** del ESP32.
- `#define RS485_DI 17`: Define que los bytes que el ESP32 transmite saldrán por el pin **D17** hacia la patilla **DI** (*Driver Input*) del transceptor.
- `#define RS485_DE 4` y `#define RS485_RE 18`: Pines digitales utilizados para gobernar el sentido de la comunicación Half-Duplex.

---

### 6.3 Inicialización del Puerto Serie por Hardware UART2

```cpp
HardwareSerial RS485Serial(2);
```
- El ESP32 posee **3 controladores UART físicos de silicio** independientes en su arquitectura.
- En lugar de recurrir a la librería `SoftwareSerial` (que emula puertos serie por software interrumpiendo constantemente al procesador y provocando pérdidas de bytes cuando el WiFi transmite), se instancia directamente el canal de hardware número 2: `RS485Serial(2)`. Esto garantiza que los bytes que llegan desde la sonda sean almacenados en un búfer FIFO de hardware de 128 bytes sin intervención de la CPU principal.

---

### 6.4 Funciones de Conmutación de Bus (`modoTransmision` y `modoRecepcion`)

```cpp
void modoTransmision() {
  digitalWrite(RS485_DE, HIGH);
  digitalWrite(RS485_RE, HIGH);
}
```
- Al poner ambos pines en estado lógico **ALTO (3.3V)**:
  - `DE = HIGH`: Los transistores de salida del MAX485 se activan, permitiendo que el flujo de datos del pin DI module el voltaje diferencial de los bornes A y B.
  - `RE = HIGH`: El receptor interno se apaga. Esto es fundamental para evitar el fenómeno de *auto-eco* (que el ESP32 lea en su búfer de entrada las mismas instrucciones que él mismo acaba de gritar hacia el bus).

```cpp
void modoRecepcion() {
  digitalWrite(RS485_DE, LOW);
  digitalWrite(RS485_RE, LOW);
}
```
- Al poner ambos pines en estado lógico **BAJO (0V)**:
  - `DE = LOW`: Los transmisores se desconectan del bus quedando en alta impedancia, dejando las líneas A y B libres para que la sonda pueda responder.
  - `RE = LOW`: Al tener lógica invertida, un cero habilita el receptor, conectando la línea de datos del bus directamente hacia el pin D16 (RX2).

---

### 6.5 Función de Consulta y Parseo `leerRegistros`

Esta es la función más crítica del firmware; ejecuta la secuencia completa de interrogación:

1. **Construcción de la Trama de 8 Bytes**:
   ```cpp
   solicitud[0] = SENSOR_ID;
   solicitud[1] = 0x03;
   solicitud[2] = highByte(registroInicial);
   solicitud[3] = lowByte(registroInicial);
   solicitud[4] = highByte(cantidad);
   solicitud[5] = lowByte(cantidad);
   ```
   Divide los enteros de 16 bits en sus componentes de 8 bits mediante las macros `highByte()` y `lowByte()` y anexa el código CRC16.
2. **Vaciado del Búfer de Entrada**:
   ```cpp
   while (RS485Serial.available()) { RS485Serial.read(); }
   ```
   Drena cualquier byte residual o ruido que haya entrado a la cola serial antes de comenzar la nueva conversación.
3. **Transmisión y Vaciado Forzado**:
   ```cpp
   modoTransmision();
   delay(2);
   RS485Serial.write(solicitud, 8);
   RS485Serial.flush();
   delay(2);
   modoRecepcion();
   ```
   La instrucción `RS485Serial.flush()` es indispensable: detiene la ejecución del código hasta que el último bit físico haya salido físicamente por el pin D17. Si se conmutara a `modoRecepcion()` antes del `flush()`, se cortaría la transmisión del último byte por la mitad.
4. **Recepción con Temporizador no Bloqueante**:
   ```cpp
   unsigned long tiempoInicio = millis();
   while (millis() - tiempoInicio < 1000) {
     if (RS485Serial.available()) {
       respuesta[indice++] = RS485Serial.read();
     }
   }
   ```
   Espera la respuesta durante un máximo de 1000 milisegundos (1 segundo). Si la sonda está apagada o desconectada, el bucle finaliza sin colgar el microcontrolador.
5. **Reconstrucción Matemática de Registros de 16 Bits**:
   ```cpp
   datos[i] = ((uint16_t)respuesta[posicion] << 8) | respuesta[posicion + 1];
   ```
   Los registros Modbus viajan en formato **Big-Endian**. El microcontrolador toma el primer byte, lo convierte a un entero de 16 bits, lo desplaza 8 posiciones a la izquierda (`<< 8`) y mediante una operación lógica `OR (|)` le incrusta el byte bajo en los 8 bits restantes.

---

### 6.6 Función de Serialización y Despacho HTTP `enviarADjango`

```cpp
void enviarADjango(uint16_t *datos) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(DJANGO_URL);
  http.addHeader("Content-Type", "application/json");

  String json = "{";
  json += "\"humedad\":" + String(datos[0]) + ",";
  ...
  json += "}";

  int codigoRespuesta = http.POST(json);
  http.end();
}
```
- **¿Por qué se arma el JSON mediante concatenación directa en lugar de usar librerías como ArduinoJson?**:
  En proyectos de campo embebidos donde la memoria RAM es valiosa y las variables son fijas, instanciar un árbol de documentos dinámicos (`DynamicJsonDocument`) consume fragmentos de memoria dinámica (*heap*). El armado directo consume menos de 120 bytes de pila (*stack*) y se libera instantáneamente al salir de la función.
- **`http.POST(json)`**: Envía la carga útil hacia el servidor Django y retorna el código de estado HTTP (`200` si fue exitoso, `401` si no está autorizado, `405` o `500` si hubo error).
- **`http.end()`**: Cierra formalmente la conexión HTTP y libera el socket TCP para prevenir fugas de memoria (*memory leaks*).

---

### 6.7 Rutinas de Ciclo de Vida: `setup()` y `loop()`

- **En `setup()`**:
  - Se fija la velocidad de la consola USB en **`115200` baudios** para no retrasar la depuración.
  - Se inicia la comunicación con el módulo MAX485 a **`4800` baudios**, velocidad fija establecida de fábrica en el firmware interno de la sonda SN-3002.
- **En `loop()`**:
  - Se implementa el patrón de temporización con `millis()`:
    ```cpp
    if (millis() - ultimaLectura >= INTERVALO)
    ```
    Esto permite que el procesador ejecute la lectura cada 5 segundos sin usar la función bloqueante `delay(5000)`. Mientras transcurren los 5 segundos, el microcontrolador mantiene activos los hilos de fondo del stack WiFi y las tareas de mantenimiento de red de FreeRTOS.

---

## 7. Integración con el Servidor Django: Del Byte al ORM

A continuación se ilustra la correspondencia exacta entre los datos crudos generados por el firmware C++ y los modelos relacionales de Django:

### 7.1 Mapeo de Registros Modbus a Parámetros Edafológicos

| Posición en Array `datos[i]` | Variable Física | Rango Bruto del Sensor | Magnitud Real Desescalada | Campo de Destino en Django |
| :---: | :--- | :---: | :---: | :--- |
| **`datos[0]`** | Humedad de Suelo | `0` a `1000` | `0.0%` a `100.0%` | `LecturaSensor.humedad` |
| **`datos[1]`** | Temperatura Edáfica | `-400` a `800` | `-40.0 °C` a `80.0 °C` | `LecturaSensor.temperatura` |
| **`datos[2]`** | Conductividad Eléctrica | `0` a `20000` | `0` a `20000 µS/cm` | `LecturaSensor.conductividad` |
| **`datos[3]`** | Potencial de Hidrógeno | `0` a `140` | `0.00` a `14.00 pH` | `LecturaSensor.ph` |
| **`datos[4]`** | Nitrógeno (N) | `0` a `1999` | `0` a `1999 mg/kg` | `LecturaSensor.nitrogeno` |
| **`datos[5]`** | Fósforo (P) | `0` a `1999` | `0` a `1999 mg/kg` | `LecturaSensor.fosforo` |
| **`datos[6]`** | Potasio (K) | `0` a `1999` | `0` a `1999 mg/kg` | `LecturaSensor.potasio` |

### 7.2 Justificación del Desescalado Decimal (`/ 10.0`)

En la vista [`apps/sensores/views.py`](file:///c:/laragon/www/TierSystem-Django/apps/sensores/views.py), la función `recibir_datos_sensor` procesa la carga JSON enviada por el ESP32:

```python
humedad = float(datos.get("humedad", 0)) / 10.0
temperatura = float(datos.get("temperatura", 0)) / 10.0
ph = float(datos.get("ph", 0)) / 10.0
```

- Los sensores industriales transmiten números enteros de 16 bits sin coma decimal.
- Si el suelo tiene una humedad del **$65.4\%$**, el sensor transmite el entero **`654`**.
- Si el suelo tiene un pH de **`6.8`**, el sensor transmite el entero **`68`**.
- El backend divide estos valores entre `10.0` para almacenar la cifra con decimales reales en las columnas de base de datos MySQL. Las variables de conductividad, nitrógeno, fósforo y potasio no requieren división ya que sus unidades industriales estándar vienen en enteros directos (µS/cm y mg/kg).

### 7.3 Interacción con el Filtro Anti-Ruido Digital (Moda y Mediana)

Cada 5 segundos, el ESP32 inserta una fila en la tabla `sensores_lecturasensor`. Cuando el laboratorista presiona el botón **"Tomar Muestra"** en la interfaz web de campo, el sistema no toma la última lectura instantánea; en su lugar, invoca la vista `captura_estable`:

1. Selecciona todas las lecturas recibidas durante los últimos **15 segundos**.
2. Calcula la **Moda Estadística** (`statistics.mode`): aísla el valor idéntico repetido en las tramas digitales y elimina cualquier distorsión capacitiva transitoria ocurrida al clavar la sonda en la tierra.
3. Si la señal tiene fluctuaciones continuas, conmuta a la **Mediana** (`statistics.median`).
4. El valor resultante, limpio de ruido, se asigna al `PuntoMuestreo` junto con las coordenadas GPS del dispositivo móvil.

---

## 8. Guía de Diagnóstico y Resolución de Problemas (Troubleshooting)

### Síntoma 1: El ESP32 no arranca y muestra `boot:0xb` al encenderse
- **Causa**: Uno o varios pines del MAX485 están conectados a pines de strapping (D2, D12 o D15).
- **Solución**: Verificar que los cables sigan rigurosamente el esquema seguro: `RO -> D16`, `DI -> D17`, `DE -> D4`, `RE -> D18`.

### Síntoma 2: El monitor serie muestra continuamente `ERROR: No se recibió respuesta de la sonda (Timeout)`
1. **Polaridad RS485 Invertida**: Los cables A y B están cruzados. **Solución**: Intercambiar los cables entre los bornes A y B del módulo HW-097 (Amarillo a Borne A, Azul a Borne B).
2. **Falta de Voltaje en la Sonda**: La sonda SN-3002 requiere mínimo **12V DC**. Si se alimenta con 5V, los transistores internos no se activan. **Solución**: Medir con un multímetro que existan entre 11.8V y 12.5V entre los cables Café (+) y Negro (−).
3. **Masa Común Desconectada**: Si el GND del ESP32 no está físicamente unido al polo negativo (−) de la fuente de 12V, no existe una referencia eléctrica de retorno, impidiendo que la señal TTL del pin RO sea detectada por el microcontrolador. **Solución**: Unir todos los cables de tierra (GND) en un único punto común.

### Síntoma 3: El monitor serie muestra `ERROR: Fallo de verificación CRC`
- **Causa**: Ruido electromagnético intenso o velocidad en baudios incorrecta.
- **Solución**: Comprobar que en `setup()` la velocidad de `RS485Serial.begin()` esté fijada exactamente en **4800 baudios**. Asegurar que los cables A y B sean un par trenzado (*twisted pair*).

### Síntoma 4: El monitor serie muestra `Fallo en la petición HTTP: connection refused` o `Código HTTP: -1`
1. **IP Incorrecta en el Firmware**: La dirección IP configurada en `DJANGO_URL` cambió (por ejemplo, si el router asignó una nueva IP por DHCP a la computadora). **Solución**: Abrir una terminal en la computadora (`cmd`), ejecutar `ipconfig`, identificar la dirección IPv4 actual y actualizar la constante `DJANGO_URL` en el código C++.
2. **Bloqueo del Firewall de Windows**: El firewall de Windows bloquea conexiones entrantes en el puerto 8000 procedentes de dispositivos externos en la red local. **Solución**: Crear una regla de entrada en el Firewall de Windows para autorizar el puerto TCP 8000 o permitir el tráfico de la aplicación Python.

---
*Fin del Documento Técnico de Firmware C++ para ESP32 — TierSystem v1.0 (2026)*
