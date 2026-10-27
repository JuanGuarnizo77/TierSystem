"""
Script de Diagnóstico: Búsqueda de Conjuntos de Datos SIPSA en Datos Abiertos Colombia.
======================================================================================
Realiza una consulta de exploración a la API de Socrata (datos.gov.co) para
localizar identificadores (UIDs) de datasets vigentes relacionados con el SIPSA del DANE.

Uso:
  python scratch/search_sipsa.py
"""

import requests

try:
    print("Buscando datasets SIPSA en el portal de Datos Abiertos de Colombia...")
    # Petición GET al catálogo de vistas y conjuntos de datos de datos.gov.co
    res = requests.get('https://www.datos.gov.co/api/views?q=SIPSA', timeout=10)
    data = res.json()
    count = 0

    # Filtrar resultados coincidentes con el sistema de información de precios
    for view in data:
        nombre = view.get('name', '').lower()
        if 'sipsa' in nombre or 'precios' in nombre:
            print(f"Nombre: {view.get('name')}")
            print(f"ID (UID): {view.get('id')}")
            count += 1
            # Limitar la salida a los primeros 5 datasets para evitar sobrecarga de terminal
            if count >= 5:
                break
except Exception as e:
    print("Error durante la consulta a datos.gov.co:", e)
