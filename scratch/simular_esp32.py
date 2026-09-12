import time
import requests
import random

DJANGO_URL = "http://127.0.0.1:8000/api/lecturas/"

print("=========================================")
print(" SIMULADOR DE SENSOR ESP32 + HW-097")
print("=========================================")
print(f"Destino: {DJANGO_URL}")
print("Enviando señales cada 5 segundos...")
print("Presiona Ctrl+C para detener.")
print("=========================================\n")

try:
    while True:
        # Generar valores base con ligera variación (ruido)
        humedad = round(random.uniform(40.0, 42.0), 1)
        temperatura = round(random.uniform(22.0, 24.0), 1)
        conductividad = round(random.uniform(1.2, 1.5), 2)
        ph = round(random.uniform(6.5, 6.8), 1)
        nitrogeno = round(random.uniform(120.0, 125.0), 1)
        fosforo = round(random.uniform(45.0, 48.0), 1)
        potasio = round(random.uniform(200.0, 210.0), 1)

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
            print(f"[*] Enviando datos... ", end="")
            response = requests.post(DJANGO_URL, json=datos, timeout=3)
            if response.status_code == 200:
                print(f"OK (Status 200) -> H:{humedad}% T:{temperatura}C")
            else:
                print(f"ERROR (Status {response.status_code})")
                print(response.text)
        except requests.exceptions.RequestException as e:
            print(f"Fallo de conexión: {e}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\nSimulador detenido.")
