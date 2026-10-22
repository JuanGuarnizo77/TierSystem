import os
import django
from django.core.management.base import BaseCommand
from apps.ia_recomendaciones.models import CultivoIdeal
from apps.terrenos.models import Terreno
from apps.solicitudes.models import SolicitudAnalisis
from core.cultivos_data import CULTIVOS_HUILA

# Diccionario de altitudes aproximadas para cultivos clave del Huila (min_msnm, max_msnm)
ALTITUDES_HUILA = {
    "Café": (1200, 2000),
    "Café Castillo": (1200, 1900),
    "Café Colombia": (1200, 1900),
    "Café Borbón": (1400, 2100),
    "Café Caturra": (1300, 2000),
    "Café Geisha": (1500, 2200),
    "Cacao": (150, 900),
    "Plátano": (0, 1600),
    "Banano": (0, 1200),
    "Aguacate Hass": (1600, 2400),
    "Aguacate Común": (0, 1500),
    "Cholupa": (400, 1200),
    "Granadilla": (1700, 2500),
    "Pitahaya Amarilla": (1000, 1800),
    "Pitahaya Roja": (800, 1600),
    "Lulo": (1500, 2400),
    "Maracuyá": (0, 1000),
    "Tomate de Árbol": (1800, 2800),
    "Mora": (1800, 2800),
    "Gulupa": (1400, 2200),
    "Uchuva": (1800, 2800),
    "Guanábana": (0, 1000),
    "Limón Tahití": (0, 1200),
    "Naranja Valencia": (0, 1400),
    "Mandarina": (0, 1400),
    "Mango Tommy": (0, 1000),
    "Papaya": (0, 1000),
    "Piña Cayena": (0, 1000),
    "Sandía": (0, 800),
    "Melón": (0, 800),
    "Guayaba": (0, 1500),
    "Maíz Tradicional": (0, 1800),
    "Maíz Híbrido": (0, 1600),
    "Arroz Secano": (0, 800),
    "Arroz Riego": (0, 800),
    "Sorgo": (0, 1000),
    "Trigo": (2000, 3000),
    "Yuca": (0, 1200),
    "Papa": (2000, 3200),
    "Arracacha": (1500, 2600),
    "Ñame": (0, 1000),
    "Batata": (0, 1000),
    "Ahuyama": (0, 1500),
    "Frijol Cargamanto": (1400, 2200),
    "Frijol Voluble": (1400, 2400),
    "Arveja": (1800, 2800),
    "Soya": (0, 1200),
    "Tomate de Mesa": (800, 2200),
    "Pimentón": (800, 2000),
    "Cebolla de Rama": (1500, 2800),
    "Cebolla Cabezona": (1500, 2800),
    "Zanahoria": (1800, 3000),
    "Lechuga": (1500, 2800),
    "Cilantro": (0, 2600),
    "Caña Panelera": (0, 1800),
    "Tabaco": (0, 1000),
    "Algodón": (0, 800),
    "Palma de Aceite": (0, 600),
}

def parse_range(range_str, default_min, default_max):
    try:
        clean = range_str.replace('%', '').replace(' ', '')
        parts = clean.split('-')
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
    except Exception:
        pass
    return default_min, default_max

class Command(BaseCommand):
    help = "Pobla la base de datos con el catálogo completo y unificado de cultivos del Huila, rangos NPK, pH, altitud e iconos."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando importación del catálogo completo de cultivos a la Base de Datos MySQL..."))
        
        # 1. Cargar datos base de seed_cultivos si existe
        seed_data = {}
        try:
            import seed_cultivos
            import inspect
            src = inspect.getsource(seed_cultivos.run)
            # Ejecutar de forma segura para extraer la lista cultivos
            local_vars = {}
            exec("import django\n" + src, {}, local_vars)
            # O alternativamente importar la lista inspeccionando el módulo
        except Exception:
            pass

        # 2. Procesar la lista completa de CULTIVOS_HUILA
        total_creados = 0
        total_actualizados = 0

        for item in CULTIVOS_HUILA:
            nombre = item["nombre"]
            categoria = item.get("categoria", "Frutal")
            clima = item.get("clima", "Templado")
            icono = item.get("img", "fa-seedling")
            
            ph_min, ph_max = parse_range(item.get("ph", "5.5 - 6.8"), 5.5, 6.8)
            hum_min, hum_max = parse_range(item.get("humedad", "60% - 80%"), 60.0, 80.0)

            # Altitudes
            alt_min, alt_max = ALTITUDES_HUILA.get(nombre, (600, 2000))
            if "Frío" in clima:
                alt_min, alt_max = max(alt_min, 1800), max(alt_max, 2800)
            elif "Cálido" in clima:
                alt_min, alt_max = min(alt_min, 200), min(alt_max, 1200)

            # Valores edafológicos por defecto adaptados a la categoría
            if categoria == "Industrial" or "Café" in nombre or "Cacao" in nombre:
                n_min, n_max = 140.0, 260.0
                p_min, p_max = 30.0, 70.0
                k_min, k_max = 150.0, 300.0
                t_min, t_max = 17.0, 25.0
                ce_min, ce_max = 0.8, 2.2
            elif categoria == "Frutal":
                n_min, n_max = 120.0, 220.0
                p_min, p_max = 25.0, 60.0
                k_min, k_max = 140.0, 280.0
                t_min, t_max = 18.0, 28.0
                ce_min, ce_max = 0.8, 2.0
            elif categoria == "Hortaliza":
                n_min, n_max = 150.0, 250.0
                p_min, p_max = 35.0, 80.0
                k_min, k_max = 160.0, 320.0
                t_min, t_max = 16.0, 26.0
                ce_min, ce_max = 1.0, 2.5
            elif categoria == "Cereal":
                n_min, n_max = 130.0, 240.0
                p_min, p_max = 25.0, 60.0
                k_min, k_max = 120.0, 240.0
                t_min, t_max = 20.0, 32.0
                ce_min, ce_max = 0.8, 2.0
            elif categoria == "Tubérculo":
                n_min, n_max = 100.0, 200.0
                p_min, p_max = 30.0, 70.0
                k_min, k_max = 180.0, 350.0
                t_min, t_max = 15.0, 28.0
                ce_min, ce_max = 0.8, 2.2
            elif categoria == "Leguminosa":
                n_min, n_max = 80.0, 160.0  # Fijan nitrógeno biológicamente
                p_min, p_max = 30.0, 65.0
                k_min, k_max = 120.0, 250.0
                t_min, t_max = 16.0, 26.0
                ce_min, ce_max = 0.8, 2.0
            else:
                n_min, n_max = 100.0, 200.0
                p_min, p_max = 25.0, 50.0
                k_min, k_max = 100.0, 220.0
                t_min, t_max = 18.0, 28.0
                ce_min, ce_max = 0.8, 2.0

            defaults = {
                "descripcion": f"Cultivo adaptado a clima {clima} en el departamento del Huila. Rango altitudinal recomendado: {alt_min}-{alt_max} msnm.",
                "categoria": categoria,
                "clima": clima,
                "icono": icono,
                "altitud_min": alt_min,
                "altitud_max": alt_max,
                "ph_min": ph_min,
                "ph_max": ph_max,
                "humedad_min": hum_min,
                "humedad_max": hum_max,
                "temperatura_min": t_min,
                "temperatura_max": t_max,
                "conductividad_min": ce_min,
                "conductividad_max": ce_max,
                "nitrogeno_min": n_min,
                "nitrogeno_max": n_max,
                "fosforo_min": p_min,
                "fosforo_max": p_max,
                "potasio_min": k_min,
                "potasio_max": k_max,
                "activo": True
            }

            obj, created = CultivoIdeal.objects.update_or_create(
                nombre=nombre,
                defaults=defaults
            )

            if created:
                total_creados += 1
            else:
                total_actualizados += 1

        self.stdout.write(self.style.SUCCESS(f"Catálogo poblado: {total_creados} nuevos creados, {total_actualizados} actualizados. Total en BD: {CultivoIdeal.objects.count()}"))

        # 3. Vincular Terrenos existentes con el catálogo
        terrenos_vinculados = 0
        for ter in Terreno.objects.all():
            if ter.cultivo_principal and not ter.cultivo_ref:
                coincidencia = CultivoIdeal.objects.filter(nombre__icontains=ter.cultivo_principal).first()
                if coincidencia:
                    ter.cultivo_ref = coincidencia
                    ter.save(update_fields=['cultivo_ref'])
                    terrenos_vinculados += 1
        
        self.stdout.write(self.style.SUCCESS(f"Terrenos vinculados relacionalmente: {terrenos_vinculados}"))

        # 4. Vincular Solicitudes existentes con el catálogo
        solicitudes_vinculadas = 0
        for sol in SolicitudAnalisis.objects.all():
            if sol.cultivo_deseado and not sol.cultivo_deseado_ref:
                coincidencia = CultivoIdeal.objects.filter(nombre__icontains=sol.cultivo_deseado).first()
                if coincidencia:
                    sol.cultivo_deseado_ref = coincidencia
                    sol.save(update_fields=['cultivo_deseado_ref'])
                    solicitudes_vinculadas += 1

        self.stdout.write(self.style.SUCCESS(f"Solicitudes vinculadas relacionalmente: {solicitudes_vinculadas}"))
        self.stdout.write(self.style.SUCCESS("Migración e importación a base de datos finalizada con éxito."))
