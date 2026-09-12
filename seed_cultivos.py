import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tiersystem.settings")
django.setup()

from apps.ia_recomendaciones.models import CultivoIdeal

def run():
    CultivoIdeal.objects.all().delete()

    cultivos = [
        {
            "nombre": "Café (Variedad Castillo)",
            "descripcion": "Alta resistencia a la roya, ideal para climas cafeteros del Huila.",
            "humedad_min": 60, "humedad_max": 80,
            "temperatura_min": 18, "temperatura_max": 24,
            "conductividad_min": 1.0, "conductividad_max": 2.5,
            "ph_min": 5.0, "ph_max": 5.5,
            "nitrogeno_min": 150, "nitrogeno_max": 250,
            "fosforo_min": 30, "fosforo_max": 60,
            "potasio_min": 150, "potasio_max": 300,
        },
        {
            "nombre": "Café (Variedad Borbón)",
            "descripcion": "Café de altísima calidad en taza, común en el sur del Huila. Muy exigente en nitrógeno.",
            "humedad_min": 55, "humedad_max": 75,
            "temperatura_min": 16, "temperatura_max": 22,
            "conductividad_min": 1.2, "conductividad_max": 2.2,
            "ph_min": 5.2, "ph_max": 6.2,
            "nitrogeno_min": 180, "nitrogeno_max": 280,
            "fosforo_min": 40, "fosforo_max": 70,
            "potasio_min": 180, "potasio_max": 320,
        },
        {
            "nombre": "Café (Variedad Caturra)",
            "descripcion": "Variedad tradicional, susceptible a roya pero excelente rendimiento. Prefiere suelos más ácidos.",
            "humedad_min": 50, "humedad_max": 70,
            "temperatura_min": 17, "temperatura_max": 25,
            "conductividad_min": 1.1, "conductividad_max": 2.4,
            "ph_min": 4.8, "ph_max": 5.8,
            "nitrogeno_min": 160, "nitrogeno_max": 240,
            "fosforo_min": 35, "fosforo_max": 65,
            "potasio_min": 160, "potasio_max": 290,
        },
        {
            "nombre": "Maíz (Híbrido Amarillo)",
            "descripcion": "Variedad forrajera muy común en el centro del Huila. Alta demanda de N y P.",
            "humedad_min": 40, "humedad_max": 70,
            "temperatura_min": 22, "temperatura_max": 30,
            "conductividad_min": 1.5, "conductividad_max": 3.0,
            "ph_min": 5.8, "ph_max": 7.0,
            "nitrogeno_min": 220, "nitrogeno_max": 320,
            "fosforo_min": 50, "fosforo_max": 90,
            "potasio_min": 120, "potasio_max": 250,
        },
        {
            "nombre": "Frijol (Cargamanto)",
            "descripcion": "Leguminosa que fija nitrógeno pero demanda un pH neutro y suelos no encharcados.",
            "humedad_min": 50, "humedad_max": 75,
            "temperatura_min": 18, "temperatura_max": 26,
            "conductividad_min": 0.8, "conductividad_max": 1.8,
            "ph_min": 6.0, "ph_max": 7.5,
            "nitrogeno_min": 80, "nitrogeno_max": 150,
            "fosforo_min": 60, "fosforo_max": 110,
            "potasio_min": 100, "potasio_max": 200,
        }
    ]

    for data in cultivos:
        CultivoIdeal.objects.create(**data)
        print(f"Creado: {data['nombre']}")

    print("Catálogo de cultivos poblado exitosamente.")

if __name__ == "__main__":
    run()
