import requests
try:
    print("Searching datasets...")
    res = requests.get('https://www.datos.gov.co/api/views?q=SIPSA', timeout=10)
    data = res.json()
    count = 0
    for view in data:
        if 'sipsa' in view.get('name', '').lower() or 'precios' in view.get('name', '').lower():
            print(f"Name: {view.get('name')}")
            print(f"ID: {view.get('id')}")
            count += 1
            if count > 5: break
except Exception as e:
    print("Error:", e)
