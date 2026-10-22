"""
Management command: actualizar_sipsa
Actualiza precios semanales SIPSA/DANE desde datos.gov.co (Socrata).
Fallback: precios de referencia hard-coded.

Uso:
    python manage.py actualizar_sipsa

Cron semanal (lunes 7am):
    0 7 * * 1 /ruta/al/venv/bin/python /ruta/manage.py actualizar_sipsa >> /var/log/sipsa.log 2>&1
"""
import requests
from datetime import date, timedelta
from django.core.management.base import BaseCommand

from apps.sipsa.models import CultivoSipsa, PrecioSemanal
from apps.sipsa.management.commands.seed_sipsa import _recalcular_predicciones


HTTP_TIMEOUT = 12

# Datasets DANE en datos.gov.co (Socrata endpoints)
APIS_DANE = [
    "https://www.datos.gov.co/resource/3sp3-mua5.json",   # Abastecimiento centrales
    "https://www.datos.gov.co/resource/8ff4-g29n.json",   # SIPSA mayoristas
    "https://www.datos.gov.co/resource/2hfu-fu5g.json",   # SIPSA abastecimiento
]

# Bootstrap fallback prices (COP/kg) — used ONLY when the DB is empty and no
# PrecioMercado records exist yet (first-run / cold-start scenario).
# Do NOT add business logic here; use _get_fallback_precio() instead.
FALLBACK_PRECIOS_BOOTSTRAP = {
    "Papa Pastusa":       {"precio": 1900},
    "Tomate Chonto":      {"precio": 3000},
    "Cebolla Cabezona":   {"precio": 1200},
    "Fríjol Cargamanto":  {"precio": 8400},
    "Zanahoria":          {"precio": 1290},
    "Plátano Hartón":     {"precio": 980},
    "Arroz Blanco":       {"precio": 3000},
    "Maíz Amarillo":      {"precio": 1400},
    "Aguacate Hass":      {"precio": 8197},
    "Yuca":               {"precio": 1000},
    # ── Cultivos canónicos ampliados ──────────────────────────────────────
    "Café":               {"precio": 16440},
    "Cacao":              {"precio": 14805},
    "Aguacate Común":     {"precio": 3200},
    "Caña Panelera":      {"precio": 4200},
    "Maracuyá":           {"precio": 2000},
    "Lulo":               {"precio": 2800},
    "Cholupa":            {"precio": 4500},
    "Sorgo":              {"precio": 1100},
    "Limón Tahití":       {"precio": 1800},
    "Guanábana":          {"precio": 3800},
    "Papaya":             {"precio": 1500},
    "Mango Tommy":        {"precio": 2200},
    "Piña Cayena":        {"precio": 1600},
    "Fríjol Bola Roja":   {"precio": 6500},
    "Granadilla":         {"precio": 3500},
    "Pitahaya":           {"precio": 7500},
    "Gulupa":             {"precio": 5000},
    "Mora":               {"precio": 4500},
    # ── Cultivos extendidos (catálogo completo ~71 cultivos) ──────────────
    "Café Castillo":      {"precio": 16440},
    "Café Colombia":      {"precio": 16440},
    "Café Caturra":       {"precio": 16440},
    "Banano":             {"precio": 800},
    "Badea":              {"precio": 2800},
    "Curuba":             {"precio": 2200},
    "Tomate de Árbol":    {"precio": 2500},
    "Tabaco Rubio":       {"precio": 4500},
    "Tabaco Negro":       {"precio": 4200},
    "Soya":               {"precio": 1800},
    "Ajonjolí":           {"precio": 3500},
    "Algodón":            {"precio": 2200},
    "Pepino":             {"precio": 1200},
    "Ají":                {"precio": 2500},
    "Cilantro":           {"precio": 3000},
    "Acelga":             {"precio": 1800},
    "Ñame":               {"precio": 1200},
    "Batata":             {"precio": 900},
    "Tilapia":            {"precio": 8500},
    "Trucha":             {"precio": 12000},
    "Naranja Valencia":   {"precio": 1200},
    "Mandarina":          {"precio": 1400},
    "Pitahaya Amarilla":  {"precio": 7500},
}


# Precio por grupo — usado como segundo nivel de fallback cuando no hay
# registro histórico en PrecioMercado para el cultivo.
_PRECIOS_GRUPO = {
    'frutas':     3000,
    'hortalizas': 2000,
    'granos':     1500,
    'tuberculos': 1200,
    'lacteos':    2500,
    'carnes':     8000,
    'pescados':   9000,
    'otros':      1800,
}


def _get_fallback_precio(cultivo):
    """
    Devuelve un precio de referencia (COP/kg) para el cultivo dado.

    Prioridad:
      1. Último PrecioMercado disponible en BD (precio histórico real).
      2. Precio genérico por grupo del cultivo.
      3. Bootstrap hardcodeado (FALLBACK_PRECIOS_BOOTSTRAP).
      4. Default universal 2000 COP/kg.
    """
    from apps.mercado.models import PrecioMercado  # import local para evitar ciclos

    # 1. Último precio histórico real
    ultimo = PrecioMercado.objects.filter(cultivo_nombre=cultivo.nombre).order_by('-fecha_creacion').first()
    if ultimo:
        return float(ultimo.precio_promedio)

    # 2. Precio genérico por grupo
    grupo = (cultivo.grupo or '').lower()
    for key, precio in _PRECIOS_GRUPO.items():
        if key in grupo:
            return precio

    # 3. Tabla bootstrap hardcodeada
    entry = FALLBACK_PRECIOS_BOOTSTRAP.get(cultivo.nombre)
    if entry:
        return float(entry['precio'])

    # 4. Default universal
    return 2000.0

MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
            'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _semana_actual():
    """Devuelve el lunes de la semana actual."""
    hoy = date.today()
    return hoy - timedelta(days=hoy.weekday())


def _label(d: date) -> str:
    """Devuelve etiqueta legible: '18 ago – 24 ago 2026'."""
    fin = d + timedelta(days=6)
    mes_ini = MESES_ES[d.month - 1]
    mes_fin = MESES_ES[fin.month - 1]
    return f"{d.day} {mes_ini} – {fin.day} {mes_fin} {fin.year}"


class Command(BaseCommand):
    help = "Actualiza precios semanales SIPSA desde datos.gov.co (Socrata) con fallback estático."

    def _guardar_precio(self, cultivo_nombre, precio, fuente, fuente_url=""):
        try:
            cultivo = CultivoSipsa.objects.get(nombre=cultivo_nombre)
        except CultivoSipsa.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"  Cultivo no encontrado: {cultivo_nombre}"))
            return False

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
        self.stdout.write(self.style.SUCCESS(f"  ✓ {cultivo_nombre}: ${precio:,}/kg ({label})"))
        return True

    def _intentar_apis_dane(self, actualizados):
        """Intenta cada endpoint Socrata y parsea filas buscando cultivos."""
        alias_map = {}
        for cultivo in CultivoSipsa.objects.filter(activo=True):
            if cultivo.nombre_dane:
                alias_map[cultivo.nombre_dane.lower()] = cultivo.nombre

        total_activos = CultivoSipsa.objects.filter(activo=True).count()

        for api_url in APIS_DANE:
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
        self.stdout.write(self.style.MIGRATE_HEADING("=== actualizar_sipsa: iniciando ==="))
        actualizados = set()

        actualizados = self._intentar_apis_dane(actualizados)

        # Fallback dinámico para cultivos no actualizados por las APIs
        cultivos_pendientes = CultivoSipsa.objects.filter(activo=True).exclude(nombre__in=actualizados)
        if cultivos_pendientes.exists():
            nombres_pendientes = [c.nombre for c in cultivos_pendientes]
            self.stdout.write(self.style.WARNING(
                f"  Fallback dinámico para: {', '.join(nombres_pendientes)}"
            ))
            for cultivo in cultivos_pendientes:
                try:
                    precio = _get_fallback_precio(cultivo)
                    self._guardar_precio(
                        cultivo.nombre, precio,
                        "Referencia SIPSA/DANE (fallback dinámico)", ""
                    )
                    actualizados.add(cultivo.nombre)
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(
                        f"  [fallback] Error en {cultivo.nombre}: {exc}"
                    ))

        # Recalcular predicciones
        _recalcular_predicciones(self)

        self.stdout.write(self.style.SUCCESS(
            f"\n=== actualizar_sipsa: {len(actualizados)} cultivos actualizados ==="
        ))
