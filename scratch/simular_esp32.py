"""
Simulador Telemétrico de Hardware: Sensor ESP32 + Sonda Edafológica 7 en 1 (HW-097).
=====================================================================================
Emula el comportamiento en campo de una sonda multiparamétrica conectada a un
microcontrolador ESP32 mediante comunicación Modbus RS485.

Comportamiento:
  1. Genera periódicamente (cada 5 segundos) valores con ligera fluctuación estocástica (ruido):
      - Humedad edáfica (%)
      - Temperatura del suelo (°C)
      - Conductividad eléctrica (dS/m)
      - Acidez / Alcalinidad (pH)
      - Nitrógeno asimilable (mg/kg)
      - Fósforo disponible (mg/kg)
      - Potasio intercambiable (mg/kg)
  2. Empaqueta la telemetría en un payload JSON y la despacha vía HTTP POST al
     endpoint de ingesta `/api/lecturas/`.
  3. Informa en tiempo real los códigos de respuesta HTTP y el estado del enlace.

Uso:
  python scratch/simular_esp32.py
"""

import time
import requests
import random

# Endpoint local del servidor TierSystem para la ingesta de telemetría de sensores
DJANGO_URL = "http://127.0.0.1:8000/api/lecturas/"

print("=========================================")
print(" SIMULADOR DE SENSOR ESP32 + HW-097")
print("=========================================")
print(f"Destino: {DJANGO_URL}")
print("Enviando señales cada 5 segundos...")
print("Presiona Ctrl+C para detener.")
print("=========================================\n")

try:
    # Bucle infinito de transmisión periódica de telemetría
    while True:
        # Generar valores base con ligera variación (ruido instrumental realista)
        humedad = round(random.uniform(40.0, 42.0), 1)
        temperatura = round(random.uniform(22.0, 24.0), 1)
        conductividad = round(random.uniform(1.2, 1.5), 2)
        ph = round(random.uniform(6.5, 6.8), 1)
        nitrogeno = round(random.uniform(120.0, 125.0), 1)
        fosforo = round(random.uniform(45.0, 48.0), 1)
        potasio = round(random.uniform(200.0, 210.0), 1)

        # Construir estructura de datos esperada por el serializer de Django
        datos = {
            "humedad": humedad,
            "temperatura": temperatura,
            "conductividad": conductividad,
            "ph": ph,
            "nitrogeno": nitrogeno,
            "fosforo": fosforo,
            "potasio": potasio
        }

        try:
            print(f"[*] Enviando datos... ", end="", flush=True)
            # Enviar solicitud POST con tiempo de espera estricto de 3 segundos
            response = requests.post(DJANGO_URL, json=datos, timeout=3)
            if response.status_code == 200:
                print(f"OK (Status 200) -> H:{humedad}% T:{temperatura}C pH:{ph}")
            else:
                print(f"ERROR (Status {response.status_code})")
                print(response.text)
        except requests.exceptions.RequestException as e:
            # Captura de fallos si el servidor local de Django aún no está iniciado
            print(f"Fallo de conexión: {e}")

        # Intervalo de muestreo entre transmisiones
        time.sleep(5)

except KeyboardInterrupt:
    # Captura limpia de interrupción por teclado (Ctrl+C)
    print("\nSimulador detenido por el usuario.")
