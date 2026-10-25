"""
Comando de Gestión Django: `actualizar_sipsa`.
==============================================
Descarga y sincroniza las cotizaciones mayoristas semanales oficiales desde
la plataforma de datos abiertos de Colombia (datos.gov.co / Socrata API) o
aplica valores de contingencia calibrados para el departamento del Huila.

Vincula cada precio al modelo canónico `Cultivo` y calcula el precio mayorista
regional Huila como un ~97% del promedio nacional reportado en centrales de abastos.

Uso:
    python manage.py actualizar_sipsa
"""

import requests
from datetime import date, timedelta
from django.core.management.base import BaseCommand

from apps.cultivos.models import Cultivo
from apps.sipsa.models import PrecioSemanal


# Tiempo límite en segundos para peticiones HTTP a la API pública de datos.gov.co
HTTP_TIMEOUT = 12

# Endpoints oficiales del DANE en datos.gov.co (Arquitectura Socrata Open Data API)
APIS_DANE = [
    "https://www.datos.gov.co/resource/3sp3-mua5.json",   # Abastecimiento centrales
    "https://www.datos.gov.co/resource/8ff4-g29n.json",   # SIPSA mayoristas
    "https://www.datos.gov.co/resource/2hfu-fu5g.json",   # SIPSA abastecimiento
]

# Tabla de cotizaciones de contingencia en caso de indisponibilidad o timeout de la API gubernamental
FALLBACK_PRECIOS = {
    "Papa Pastusa":       {"precio": 2260},
    "Tomate Chonto":      {"precio": 3300},
    "Cebolla Cabezona":   {"precio": 3120},
    "Fríjol Cargamanto":  {"precio": 11750},
    "Zanahoria":          {"precio": 1280},
    "Plátano Hartón":     {"precio": 1850},
    "Arroz Blanco":       {"precio": 2130},
    "Maíz Amarillo":      {"precio": 1530},
    "Aguacate Hass":      {"precio": 7500},
    "Yuca":               {"precio": 995},
}


def _semana_actual():
    """Calcula y retorna la fecha correspondiente al día lunes de la semana actual."""
    hoy = date.today()
    return hoy - timedelta(days=hoy.weekday())


def _label(d: date) -> str:
    """Genera la etiqueta estandarizada de semana según la norma ISO 8601 (ej. 'Sem 42-2026')."""
    iso = d.isocalendar()
    return f"Sem {iso[1]}-{iso[0]}"


class Command(BaseCommand):
    """Actualiza precios semanales SIPSA desde datos.gov.co (Socrata) con contingencia estática."""
    help = "Actualiza precios semanales SIPSA desde datos.gov.co (Socrata) con fallback estático."

    def _guardar_precio(self, cultivo_nombre, precio, fuente, fuente_url=""):
        """
        Inserta o actualiza un registro en `PrecioSemanal`.

        Aplica la regla de negocio del Huila:
          `precio_local = round(precio * 0.97, 2)`
        """
        cultivo = Cultivo.objects.filter(nombre__icontains=cultivo_nombre.split()[0]).first()
        if not cultivo:
            cultivo, _ = Cultivo.objects.get_or_create(nombre=cultivo_nombre)

        semana_lunes = _semana_actual()
        label = _label(semana_lunes)

        PrecioSemanal.objects.update_or_create(
            cultivo=cultivo,
            fecha_semana=semana_lunes,
            defaults={
                'semana_label': label,
                'precio_kg': precio,
                'precio_local': round(precio * 0.97, 2),
                'fuente': fuente,
                'fuente_url': fuente_url,
            }
        )
        self.stdout.write(self.style.SUCCESS(f"  ✓ {cultivo.nombre}: ${precio:,}/kg ({label})"))
        return True

    def _intentar_apis_dane(self, actualizados):
        """
        Consume secuencialmente los endpoints Socrata del DANE y empareja registros con el catálogo.

        Mapea sinónimos mediante `nombre_dane` y `nombre` para asegurar la homologación exacta.
        """
        alias_map = {}
        for cultivo in Cultivo.objects.filter(activo=True):
            if cultivo.nombre_dane:
                alias_map[cultivo.nombre_dane.lower()] = cultivo.nombre
            alias_map[cultivo.nombre.lower()] = cultivo.nombre

        total_activos = Cultivo.objects.filter(activo=True).count()

        for api_url in APIS_DANE:
            # Si ya se completaron todos los cultivos del catálogo, finaliza la búsqueda
            if len(actualizados) >= total_activos:
                break
            try:
                resp = requests.get(
                    api_url,
                    params={"$limit": 1000, "$order": "fecha DESC"},
                    timeout=HTTP_TIMEOUT,
                    headers={"User-Agent": "TierSystem/1.0 (info@tiersystem.co)"},
                )
                resp.raise_for_status()
                rows = resp.json()
                if not isinstance(rows, list):
                    continue
                self.stdout.write(f"  [DANE] {api_url} → {len(rows)} filas")

                for row in rows:
                    nombre_raw = str(
                        row.get("producto") or row.get("nombre_producto") or ""
                    ).lower()
                    precio_raw = (
                        row.get("precio_kg") or row.get("precio") or row.get("precio_promedio")
                    )

                    for alias, nombre_cultivo in alias_map.items():
                        if nombre_cultivo in actualizados:
                            continue
                        if alias in nombre_raw:
                            try:
                                precio = float(str(precio_raw).replace(",", "."))
                                # Validación de plausibilidad de precio (filtra errores o valores extremos)
                                if 50 < precio < 200_000:
                                    self._guardar_precio(
                                        nombre_cultivo, precio,
                                        f"DANE Socrata ({api_url})", api_url
                                    )
                                    actualizados.add(nombre_cultivo)
                            except (TypeError, ValueError):
                                pass
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"  [DANE] {api_url}: {exc}"))
        return actualizados

    def handle(self, *args, **options):
        """Punto de entrada del comando de gestión."""
        self.stdout.write(self.style.MIGRATE_HEADING("=== actualizar_sipsa: iniciando ==="))
        actualizados = set()

        # Fase 1: Ingesta desde endpoints REST de datos.gov.co
        actualizados = self._intentar_apis_dane(actualizados)

        # Fase 2: Aplicación de contingencia para cultivos faltantes
        pendientes = [n for n in FALLBACK_PRECIOS if n not in actualizados]
        if pendientes:
            self.stdout.write(self.style.WARNING(
                f"  Fallback estático para: {', '.join(pendientes)}"
            ))
            for nombre in pendientes:
                datos = FALLBACK_PRECIOS[nombre]
                self._guardar_precio(
                    nombre, datos['precio'],
                    "Referencia SIPSA/DANE (fallback)", ""
                )
                actualizados.add(nombre)

        self.stdout.write(self.style.SUCCESS(
            f"\n=== actualizar_sipsa: {len(actualizados)} precios actualizados exitosamente ==="
        ))
