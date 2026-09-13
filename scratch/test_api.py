import requests
try:
    print("Fetching...")
    res = requests.get('https://www.datos.gov.co/resource/mqa9-ndae.json?$limit=5', timeout=10)
    print("Status:", res.status_code)
    print("Data:", res.json())
except Exception as e:
    print("Error:", e)
