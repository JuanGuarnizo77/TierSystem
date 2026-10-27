"""
Script de Prueba: Conectividad y Consulta al Endpoint Socrata del DANE / SIPSA.
==============================================================================
Verifica la disponibilidad de red y la estructura del payload JSON suministrado
por la API pública de datos abiertos de Colombia para la serie de precios SIPSA (`mqa9-ndae`).

Uso:
  python scratch/test_api.py
"""

import requests

try:
    print("Consultando API de Datos Abiertos (Dataset SIPSA mqa9-ndae)...")
    # Petición GET solicitando los primeros 5 registros del recurso público
    res = requests.get('https://www.datos.gov.co/resource/mqa9-ndae.json?$limit=5', timeout=10)
    print("Código de estado HTTP:", res.status_code)
    print("Muestra de datos recibida:")
    print(res.json())
except Exception as e:
    print("Excepción al intentar conectar con la API de datos abiertos:", e)
