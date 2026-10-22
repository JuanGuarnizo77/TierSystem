"""
Management command: actualizar_precios
Scrapes real-time prices for café (preciocafe.com) and cacao (Agronet),
then tries Socrata/DANE APIs for remaining crops. Falls back to static
reference prices (Oct-2026) if all external sources fail.

Usage:
    python manage.py actualizar_precios
"""
import re
import requests
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.mercado.models import PrecioMercado
from apps.sipsa.models import CultivoSipsa

# ---------------------------------------------------------------------------
# Helpers para etiqueta de semana legible
# ---------------------------------------------------------------------------
MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
            'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _label(d: date) -> str:
    """Devuelve etiqueta legible: '18 ago – 24 ago 2026'."""
    fin = d + timedelta(days=6)
    mes_ini = MESES_ES[d.month - 1]
    mes_fin = MESES_ES[fin.month - 1]
    return f"{d.day} {mes_ini} – {fin.day} {mes_fin} {fin.year}"


def _semana_label_actual() -> str:
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    return _label(lunes)


# ---------------------------------------------------------------------------
# Static fallback prices (Oct-2026 reference, COP/kg)
# ---------------------------------------------------------------------------
PRECIOS_ACTUALIZADOS_OCT_2026 = {
    "Maíz Amarillo":    {"precio": 1400,  "unidad": "kg",              "tendencia": "Alza",    "variacion": 5.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Café":             {"precio": 16440, "unidad": "kg pergamino",    "tendencia": "Baja",    "variacion": -1.5, "fuente": "Referencia FNC Oct-2026"},
    "Cacao":            {"precio": 14805, "unidad": "kg grano seco",   "tendencia": "Baja",    "variacion": -0.5, "fuente": "Referencia Fedecacao Oct-2026"},
    "Plátano Hartón":   {"precio": 980,   "unidad": "kg",             "tendencia": "Alza",    "variacion": 1.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Fríjol Cargamanto":{"precio": 8400,  "unidad": "kg cargamanto",  "tendencia": "Alza",    "variacion": 6.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Aguacate Hass":    {"precio": 8197,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 9.0,  "fuente": "Referencia Asohofrucol Oct-2026"},
    "Papa Pastusa":     {"precio": 1900,  "unidad": "kg",             "tendencia": "Baja",    "variacion": -5.0, "fuente": "Referencia Fedepapa Oct-2026"},
    "Tomate Chonto":    {"precio": 3000,  "unidad": "kg chonto",      "tendencia": "Baja",    "variacion": -2.0, "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Arroz Blanco":     {"precio": 3000,  "unidad": "kg paddy verde", "tendencia": "Estable", "variacion": 0.0,  "fuente": "Referencia Fedearroz Oct-2026"},
    # ── Cultivos canónicos ampliados ─────────────────────────────────────
    "Yuca":             {"precio": 1000,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 2.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Aguacate Común":   {"precio": 3200,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 4.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Caña Panelera":    {"precio": 4200,  "unidad": "kg panela",      "tendencia": "Alza",    "variacion": 1.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Maracuyá":         {"precio": 2000,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 7.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Lulo":             {"precio": 2800,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 3.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Cholupa":          {"precio": 4500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 10.0, "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Sorgo":            {"precio": 1100,  "unidad": "kg",             "tendencia": "Estable", "variacion": 0.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Guanábana":        {"precio": 3800,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 2.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Papaya":           {"precio": 1500,  "unidad": "kg",             "tendencia": "Baja",    "variacion": -3.0, "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Mango Tommy":      {"precio": 2200,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 1.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Piña Cayena":      {"precio": 1600,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 4.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Cebolla Cabezona": {"precio": 1200,  "unidad": "kg",             "tendencia": "Baja",    "variacion": -3.0, "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Zanahoria":        {"precio": 1290,  "unidad": "kg",             "tendencia": "Baja",    "variacion": -3.0, "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Fríjol Bola Roja": {"precio": 6500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 4.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Granadilla":       {"precio": 3500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 5.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Pitahaya":         {"precio": 7500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 8.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Gulupa":           {"precio": 5000,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 6.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Mora":             {"precio": 4500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 7.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    # ── Catálogo extendido (~71 cultivos) ────────────────────────────────
    "Café Castillo":    {"precio": 16440, "unidad": "kg pergamino",   "tendencia": "Baja",    "variacion": -1.5, "fuente": "Referencia FNC Oct-2026"},
    "Café Colombia":    {"precio": 16440, "unidad": "kg pergamino",   "tendencia": "Baja",    "variacion": -1.5, "fuente": "Referencia FNC Oct-2026"},
    "Café Caturra":     {"precio": 16440, "unidad": "kg pergamino",   "tendencia": "Baja",    "variacion": -1.5, "fuente": "Referencia FNC Oct-2026"},
    "Banano":           {"precio": 800,   "unidad": "kg",             "tendencia": "Alza",    "variacion": 2.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Badea":            {"precio": 2800,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 3.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Curuba":           {"precio": 2200,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 4.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Tomate de Árbol":  {"precio": 2500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 3.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Tabaco Rubio":     {"precio": 4500,  "unidad": "kg",             "tendencia": "Estable", "variacion": 0.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Tabaco Negro":     {"precio": 4200,  "unidad": "kg",             "tendencia": "Estable", "variacion": 0.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Soya":             {"precio": 1800,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 2.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Ajonjolí":         {"precio": 3500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 3.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Algodón":          {"precio": 2200,  "unidad": "kg semilla",     "tendencia": "Estable", "variacion": 0.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Pepino":           {"precio": 1200,  "unidad": "kg",             "tendencia": "Baja",    "variacion": -2.0, "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Ají":              {"precio": 2500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 5.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Cilantro":         {"precio": 3000,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 4.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Acelga":           {"precio": 1800,  "unidad": "kg",             "tendencia": "Estable", "variacion": 0.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Ñame":             {"precio": 1200,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 2.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Batata":           {"precio": 900,   "unidad": "kg",             "tendencia": "Estable", "variacion": 0.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Tilapia":          {"precio": 8500,  "unidad": "kg en pie",      "tendencia": "Alza",    "variacion": 3.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Trucha":           {"precio": 12000, "unidad": "kg en pie",      "tendencia": "Alza",    "variacion": 2.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Limón Tahití":     {"precio": 1500,  "unidad": "kg",             "tendencia": "Baja",    "variacion": -2.0, "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Naranja Valencia": {"precio": 1200,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 3.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Mandarina":        {"precio": 1400,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 2.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
    "Pitahaya Amarilla":{"precio": 7500,  "unidad": "kg",             "tendencia": "Alza",    "variacion": 6.0,  "fuente": "Referencia SIPSA/DANE Oct-2026"},
}

# ---------------------------------------------------------------------------
# Socrata/DANE API endpoints for remaining crops
# ---------------------------------------------------------------------------
APIS_SOCRATA = [
    "https://www.datos.gov.co/resource/8ff4-g29n.json",   # SIPSA mayoristas
    "https://www.datos.gov.co/resource/2hfu-fu5g.json",   # SIPSA abastecimiento
    "https://www.datos.gov.co/resource/n2yc-4mtx.json",   # SIPSA precios alimentos
]

# Timeout for external HTTP requests (seconds)
HTTP_TIMEOUT = 10


class Command(BaseCommand):
    help = "Actualiza precios de mercado desde fuentes externas (preciocafe.com, Agronet, DANE)."

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _guardar_precio(self, cultivo, precio_kg, unidad, tendencia, variacion, fuente, fuente_url=""):
        """Persiste o actualiza un registro PrecioMercado y enlaza FK a CultivoSipsa."""
        obj, created = PrecioMercado.objects.update_or_create(
            cultivo_nombre=cultivo,
            defaults={
                "region": "Huila",
                "precio_promedio": round(precio_kg, 2),
                "precio_local": round(precio_kg * 0.97, 2),  # local ~3% below national
                "unidad": unidad,
                "tendencia": tendencia,
                "variacion_porcentaje": variacion,
                "fuente": fuente,
                "semana_sipsa": _semana_label_actual(),
                "fuente_url": fuente_url,
            },
        )
        # Link FK to canonical CultivoSipsa catalogue
        if obj.cultivo_id is None:
            cultivo_obj = CultivoSipsa.objects.filter(nombre=cultivo).first()
            if cultivo_obj:
                obj.cultivo = cultivo_obj
                obj.save(update_fields=['cultivo'])
        action = "creado" if created else "actualizado"
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ Cultivo: {cultivo} — ${precio_kg:,.0f}/{unidad} ({action})"
            )
        )
        return True

    # ------------------------------------------------------------------
    # Café scraping — preciocafe.com
    # ------------------------------------------------------------------

    def actualizar_cafe(self):
        """Intenta obtener el precio de la carga de café desde preciocafe.com."""
        url = "https://preciocafe.com"
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            # Regex for prices with format $1.234.567 or 1.234.567 (7-10 digit Colombian prices)
            patron = r'[\$]?\s*([\d]{1}[.,\d]{6,9})'
            candidatos = re.findall(patron, resp.text)
            for raw in candidatos:
                # Normalise: remove dots used as thousands separators, keep comma-decimal
                limpio = raw.replace('.', '').replace(',', '.')
                try:
                    precio_carga = float(limpio)
                    if 800_000 < precio_carga < 8_000_000:
                        precio_kg = round(precio_carga / 125, 2)
                        self.stdout.write(f"  [café] precio carga encontrado: ${precio_carga:,.0f} → ${precio_kg:,.0f}/kg")
                        return self._guardar_precio(
                            "Café", precio_kg, "kg pergamino", "Alza", 0.0,
                            "preciocafe.com (scraping)", url
                        )
                except ValueError:
                    continue
            self.stdout.write(self.style.WARNING("  [café] No se encontró precio válido en preciocafe.com"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  [café] Error al consultar preciocafe.com: {exc}"))
        return False

    # ------------------------------------------------------------------
    # Cacao scraping — Agronet
    # ------------------------------------------------------------------

    def actualizar_cacao(self):
        """Intenta obtener el precio de referencia de cacao desde Agronet."""
        url = "https://agronet.gov.co/noticias/precio-de-referencia-semanal-del-cacao"
        patrones = [
            r'precio[^\d]*\$?\s*([\d]{1,3}(?:[.,]\d{3})+)',
            r'([\d]{2,3}[.,]\d{3})\s*(?:pesos|COP|\/kg)',
            r'cacao[^\d]*([\d]{5,6})',
        ]
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            for patron in patrones:
                m = re.search(patron, resp.text, re.IGNORECASE)
                if m:
                    raw = m.group(1).replace('.', '').replace(',', '')
                    try:
                        precio_kg = float(raw)
                        if 5_000 < precio_kg < 50_000:
                            self.stdout.write(f"  [cacao] precio encontrado: ${precio_kg:,.0f}/kg")
                            return self._guardar_precio(
                                "Cacao", precio_kg, "kg grano seco", "Alza", 0.0,
                                "Agronet precio referencia semanal", url
                            )
                    except ValueError:
                        continue
            self.stdout.write(self.style.WARNING("  [cacao] No se encontró precio válido en Agronet"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  [cacao] Error al consultar Agronet: {exc}"))
        return False

    # ------------------------------------------------------------------
    # DANE / Socrata API
    # ------------------------------------------------------------------

    # Map of crop names that may appear in the DANE datasets
    CULTIVOS_DANE = {
        "Maíz Amarillo":    ["maiz", "maíz", "maize", "maiz amarillo"],
        "Plátano Hartón":   ["platano harton", "plátano hartón", "platano", "plátano", "banano"],
        "Fríjol Cargamanto":["frijol cargamanto", "fríjol cargamanto", "frijol", "fríjol", "frejol"],
        "Aguacate Hass":    ["aguacate hass", "aguacate", "hass"],
        "Papa Pastusa":     ["papa pastusa", "papa"],
        "Tomate Chonto":    ["tomate chonto", "tomate"],
        "Arroz Blanco":     ["arroz blanco", "arroz"],
        "Yuca":             ["yuca"],
        "Cebolla Cabezona": ["cebolla cabezona", "cebolla"],
        "Zanahoria":        ["zanahoria"],
        "Aguacate Común":   ["aguacate comun", "aguacate común"],
        "Caña Panelera":    ["cana panelera", "caña panelera", "panela"],
        "Maracuyá":         ["maracuya", "maracuyá"],
        "Sorgo":            ["sorgo"],
        "Guanábana":        ["guanabana", "guanábana"],
        "Papaya":           ["papaya"],
        "Mango Tommy":      ["mango tommy", "mango"],
        "Piña Cayena":      ["pina cayena", "piña cayena"],
        # ── Catálogo extendido ─────────────────────────────────────────────
        "Café Castillo":    ["cafe castillo", "café castillo", "castillo"],
        "Café Colombia":    ["cafe colombia", "café colombia", "variedad colombia"],
        "Café Caturra":     ["cafe caturra", "café caturra", "caturra"],
        "Banano":           ["banano", "banana"],
        "Granadilla":       ["granadilla"],
        "Gulupa":           ["gulupa"],
        "Cholupa":          ["cholupa"],
        "Pitahaya Amarilla":["pitahaya amarilla", "pitahaya"],
        "Pitahaya":         ["pitahaya roja"],
        "Badea":            ["badea"],
        "Curuba":           ["curuba"],
        "Lulo":             ["lulo", "naranjilla"],
        "Mora":             ["mora"],
        "Tomate de Árbol":  ["tomate de arbol", "tomate de árbol", "tomate arbol"],
        "Tabaco Rubio":     ["tabaco rubio", "tabaco"],
        "Tabaco Negro":     ["tabaco negro"],
        "Soya":             ["soya", "soja"],
        "Ajonjolí":         ["ajonjoli", "ajonjolí", "sesamo"],
        "Algodón":          ["algodon", "algodón", "cotton"],
        "Pepino":           ["pepino", "pepino cohombro"],
        "Ají":              ["aji", "ají", "chile"],
        "Cilantro":         ["cilantro", "coriandro"],
        "Acelga":           ["acelga"],
        "Ñame":             ["name", "ñame"],
        "Batata":           ["batata", "camote", "boniato"],
        "Tilapia":          ["tilapia", "mojarra"],
        "Trucha":           ["trucha"],
        "Limón Tahití":     ["limon tahiti", "limón tahití", "limon"],
        "Naranja Valencia": ["naranja valencia", "naranja"],
        "Mandarina":        ["mandarina"],
    }

    def actualizar_via_socrata(self, actualizados):
        """Queries the Socrata endpoints and saves prices for each remaining crop."""
        pendientes = {k for k in self.CULTIVOS_DANE if k not in actualizados}
        if not pendientes:
            return actualizados

        for api_url in APIS_SOCRATA:
            if not pendientes:
                break
            try:
                resp = requests.get(
                    api_url,
                    params={"$limit": 500},
                    timeout=HTTP_TIMEOUT,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
                rows = resp.json()
                if not isinstance(rows, list):
                    continue
                self.stdout.write(f"  [DANE] {api_url} → {len(rows)} filas")

                # Index rows by possible product name columns
                for cultivo in list(pendientes):
                    alias = self.CULTIVOS_DANE[cultivo]
                    for row in rows:
                        nombre_producto = str(
                            row.get("producto", row.get("nombre_producto", row.get("producto_nombre", "")))
                        ).lower()
                        if any(a in nombre_producto for a in alias):
                            # Try to extract price from common column names
                            for col in ("precio_kg", "precio", "precio_promedio", "valor_kg", "valor"):
                                val = row.get(col)
                                if val is not None:
                                    try:
                                        precio = float(str(val).replace(",", "."))
                                        if 100 < precio < 100_000:
                                            self.stdout.write(
                                                f"  [DANE] {cultivo}: ${precio:,.0f}/kg (col={col})"
                                            )
                                            static = PRECIOS_ACTUALIZADOS_OCT_2026[cultivo]
                                            self._guardar_precio(
                                                cultivo, precio,
                                                static["unidad"],
                                                static["tendencia"],
                                                static["variacion"],
                                                f"DANE Socrata ({api_url})",
                                                api_url,
                                            )
                                            pendientes.discard(cultivo)
                                            actualizados.add(cultivo)
                                            break
                                    except ValueError:
                                        continue
                            break

            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"  [DANE] Error en {api_url}: {exc}"))

        return actualizados

    # ------------------------------------------------------------------
    # Main handle
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== actualizar_precios: iniciando ==="))

        actualizados = set()

        # 1. Café
        try:
            if self.actualizar_cafe():
                actualizados.add("Café")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  [café] Excepción inesperada: {exc}"))

        # 2. Cacao
        try:
            if self.actualizar_cacao():
                actualizados.add("Cacao")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  [cacao] Excepción inesperada: {exc}"))

        # 3. Remaining via Socrata/DANE
        try:
            actualizados = self.actualizar_via_socrata(actualizados)
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"  [DANE] Excepción inesperada: {exc}"))

        # 4. Fallback for anything still missing
        pendientes_fallback = [c for c in PRECIOS_ACTUALIZADOS_OCT_2026 if c not in actualizados]
        if pendientes_fallback:
            self.stdout.write(
                self.style.WARNING(
                    f"  Aplicando fallback estático para: {', '.join(pendientes_fallback)}"
                )
            )
            for cultivo in pendientes_fallback:
                datos = PRECIOS_ACTUALIZADOS_OCT_2026[cultivo]
                try:
                    self._guardar_precio(
                        cultivo,
                        datos["precio"],
                        datos["unidad"],
                        datos["tendencia"],
                        datos["variacion"],
                        datos["fuente"],
                        "",
                    )
                    actualizados.add(cultivo)
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"  [fallback] Error en {cultivo}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\n=== actualizar_precios: completado — {len(actualizados)} cultivos actualizados ==="
            )
        )
