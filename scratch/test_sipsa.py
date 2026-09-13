import requests

url = "https://www.datos.gov.co/api/views?q=SIPSA"
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    for view in data[:5]:
        print(view['name'], view['id'])
else:
    print("Error:", response.status_code)
