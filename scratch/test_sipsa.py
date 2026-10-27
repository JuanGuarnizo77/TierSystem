"""
Script de Exploración: Identificación de Vistas SIPSA en Datos Abiertos.
========================================================================
Realiza una consulta a la API de vistas de datos.gov.co para listar los nombres
e identificadores de los primeros 5 conjuntos de datos catalogados bajo el término 'SIPSA'.

Uso:
  python scratch/test_sipsa.py
"""

import requests

url = "https://www.datos.gov.co/api/views?q=SIPSA"
response = requests.get(url, timeout=10)

if response.status_code == 200:
    data = response.json()
    print("Vistas SIPSA encontradas (Top 5):")
    # Iterar sobre las primeras 5 vistas e imprimir su denominación y código identificador único
    for view in data[:5]:
        print(f"Denominación: {view['name']} | ID: {view['id']}")
else:
    print(f"Error en la consulta: Código HTTP {response.status_code}")
