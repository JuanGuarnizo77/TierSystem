"""
Management command: seed_compradores_huila
Registra los 12 compradores oficiales del Huila en el modelo Comprador.
Idempotente (update_or_create por nombre), seguro de correr múltiples veces.

Uso:
    python manage.py seed_compradores_huila
"""
from django.core.management.base import BaseCommand

from apps.mercado.models import Comprador


# ──────────────────────────────────────────────────────────────────────────────
# Catálogo de compradores oficiales del Huila
# Campos mapeados al schema exacto del modelo Comprador:
#   nombre, tipo, municipio, contacto, cultivos_interes,
#   precio_referencia, email, whatsapp, sitio_web
# ──────────────────────────────────────────────────────────────────────────────
COMPRADORES_HUILA = [
    {
        "nombre": "SURABASTOS S.A. Propiedad Horizontal",
        "tipo": "Mayorista",
        "municipio": "Neiva, Huila",
        "contacto": "6088703840",
        "cultivos_interes": (
            "Tomate Chonto, Tomate Larga Vida, Cebolla Cabezona, Cebolla Cabezona Roja, "
            "Cebolla Junca, Pimentón, Habichuela, Pepino, Ají, Cilantro, Acelga, Zanahoria, "
            "Papa Pastusa, Papa Criolla, Yuca, Ñame, Batata, Maracuyá, Lulo, Cholupa, "
            "Granadilla, Gulupa, Badea, Curuba, Mora, Tomate de Árbol, Pitahaya Amarilla, "
            "Mandarina, Naranja Valencia, Aguacate Hass, Aguacate Lorena, Mango Tommy, "
            "Mango de Hilacha, Plátano Hartón, Plátano Dominico, Banano, Limón Tahití, "
            "Arroz de Riego, Arroz Secano, Maíz Amarillo, Maíz Blanco, Fríjol Cargamanto, "
            "Fríjol Radical, Fríjol Bola Roja, Sorgo"
        ),
        "precio_referencia": "Precio plaza mayorista Neiva",
        "email": "comercial@surabastos.com",
        "whatsapp": "",
        "sitio_web": "https://www.surabastos.com",
    },
    {
        "nombre": "CADEFIHUILA — Cooperativa Departamental de Caficultores del Huila",
        "tipo": "Cooperativa",
        "municipio": "Neiva, Huila",
        "contacto": "(608) 871 5151",
        "cultivos_interes": (
            "Café, Café Castillo, Café Colombia, Café Caturra, Café Típica, "
            "Café Borbón, Café Tabí"
        ),
        "precio_referencia": "FNC precio interno carga",
        "email": "info@cadefihuila.com.co",
        "whatsapp": "",
        "sitio_web": "https://www.cadefihuila.com.co",
    },
    {
        "nombre": "Federación Nacional de Cafeteros — Comité Huila",
        "tipo": "Cooperativa",
        "municipio": "Neiva, Huila",
        "contacto": "(608) 871 0060",
        "cultivos_interes": (
            "Café, Café Castillo, Café Colombia, Café Caturra, Café Típica, "
            "Café Borbón, Café Tabí"
        ),
        "precio_referencia": "Precio interno FNC",
        "email": "",
        "whatsapp": "",
        "sitio_web": "https://huila.federaciondecafeteros.org",
    },
    {
        "nombre": "COOAGROHUILA — Cooperativa Agropecuaria del Huila",
        "tipo": "Cooperativa",
        "municipio": "Neiva, Huila",
        "contacto": "",
        "cultivos_interes": (
            "Café, Café Castillo, Café Colombia, Café Caturra, Café Típica, "
            "Café Borbón, Café Tabí, Cacao, Plátano Hartón, Plátano Dominico, "
            "Aguacate Hass, Aguacate Lorena, Caña Panelera"
        ),
        "precio_referencia": "",
        "email": "",
        "whatsapp": "",
        "sitio_web": "",
    },
    {
        "nombre": "ASOHECA — Asociación de Reforestadores y Cultivadores de Caucho del Huila",
        "tipo": "Exportador",
        "municipio": "Neiva, Huila",
        "contacto": "",
        "cultivos_interes": (
            "Aguacate Hass, Aguacate Lorena, Cacao, Café, Café Castillo, Café Colombia, "
            "Café Caturra, Café Típica, Café Borbón, Café Tabí, Palma de Aceite"
        ),
        "precio_referencia": "",
        "email": "",
        "whatsapp": "",
        "sitio_web": "",
    },
    {
        "nombre": "Almacén Central R.S.A. S.A.S",
        "tipo": "Mayorista",
        "municipio": "Neiva, Huila",
        "contacto": "6088703840",
        "cultivos_interes": (
            "Tomate Chonto, Tomate Larga Vida, Cebolla Cabezona, Cebolla Cabezona Roja, "
            "Pimentón, Habichuela, Pepino, Zanahoria, Papa Pastusa, Papa Criolla, Yuca, "
            "Maíz Amarillo, Maíz Blanco, Fríjol Cargamanto, Arroz de Riego, Sorgo"
        ),
        "precio_referencia": "Precio Surabastos",
        "email": "",
        "whatsapp": "",
        "sitio_web": "",
    },
    {
        "nombre": "Agrisur Distribuciones Ltda.",
        "tipo": "Mayorista",
        "municipio": "Neiva, Huila",
        "contacto": "",
        "cultivos_interes": (
            "Tomate Chonto, Cebolla Cabezona, Papa Pastusa, Yuca, Maíz Amarillo, "
            "Fríjol Cargamanto, Arroz de Riego, Sorgo, Aguacate Hass, Plátano Hartón"
        ),
        "precio_referencia": "",
        "email": "",
        "whatsapp": "",
        "sitio_web": "",
    },
    {
        "nombre": "Distribuciones Agropecuarias Mi Campo S.A.S",
        "tipo": "Mayorista",
        "municipio": "Neiva, Huila",
        "contacto": "",
        "cultivos_interes": (
            "Tomate Chonto, Tomate Larga Vida, Cebolla Cabezona, Pimentón, Habichuela, "
            "Papa Pastusa, Papa Criolla, Yuca, Maíz Amarillo, Fríjol Cargamanto, "
            "Arroz de Riego, Plátano Hartón, Banano"
        ),
        "precio_referencia": "",
        "email": "",
        "whatsapp": "",
        "sitio_web": "",
    },
    {
        "nombre": "ICBF — Encuentros Agroalimentarios Huila",
        "tipo": "Institucional",
        "municipio": "Neiva, Huila",
        "contacto": "018000918080",
        "cultivos_interes": (
            "Tomate Chonto, Tomate Larga Vida, Cebolla Cabezona, Cebolla Cabezona Roja, "
            "Cebolla Junca, Pimentón, Habichuela, Pepino, Zanahoria, Acelga, Cilantro, "
            "Papa Pastusa, Papa Criolla, Yuca, Ñame, Batata, Maracuyá, Lulo, Banano, "
            "Plátano Hartón, Plátano Dominico, Mango Tommy, Limón Tahití, Naranja Valencia, "
            "Maíz Amarillo, Arroz de Riego, Fríjol Cargamanto, Aguacate Hass, Tilapia, Trucha"
        ),
        "precio_referencia": "Precio institucional ICBF",
        "email": "",
        "whatsapp": "",
        "sitio_web": "https://www.icbf.gov.co",
    },
    {
        "nombre": "Gobernación del Huila — Mercados Campesinos Institucionales",
        "tipo": "Institucional",
        "municipio": "Neiva, Huila",
        "contacto": "(608) 873 1012",
        "cultivos_interes": (
            "Tomate Chonto, Tomate Larga Vida, Cebolla Cabezona, Pimentón, Habichuela, "
            "Zanahoria, Papa Pastusa, Yuca, Maíz Amarillo, Fríjol Cargamanto, Arroz de Riego, "
            "Plátano Hartón, Banano, Aguacate Hass, Maracuyá, Lulo, Mora, Granadilla, "
            "Cacao, Café, Caña Panelera, Tilapia, Trucha"
        ),
        "precio_referencia": "Precio productor directo",
        "email": "",
        "whatsapp": "",
        "sitio_web": "https://www.huila.gov.co",
    },
    {
        "nombre": "Cámara de Comercio del Huila — Ruedas de Negocio",
        "tipo": "Institucional",
        "municipio": "Neiva, Huila",
        "contacto": "(608) 871 2421",
        "cultivos_interes": (
            "Café, Café Castillo, Café Colombia, Café Caturra, Café Típica, Café Borbón, "
            "Café Tabí, Cacao, Aguacate Hass, Aguacate Lorena, Plátano Hartón, Plátano Dominico, "
            "Maracuyá, Lulo, Cholupa, Granadilla, Gulupa, Badea, Mora, Pitahaya Amarilla, "
            "Tomate Chonto, Cebolla Cabezona, Pimentón, Papa Pastusa, Yuca, Tilapia, Trucha, "
            "Arroz de Riego, Maíz Amarillo, Fríjol Cargamanto, Soya, Tabaco Rubio, Palma de Aceite"
        ),
        "precio_referencia": "",
        "email": "",
        "whatsapp": "",
        "sitio_web": "https://www.cchuila.org",
    },
    {
        "nombre": "CEAGRODEX DEL HUILA S.A.",
        "tipo": "Exportador",
        "municipio": "Neiva, Huila",
        "contacto": "",
        "cultivos_interes": (
            "Aguacate Hass, Aguacate Lorena, Cacao, Café, Café Castillo, Café Colombia, "
            "Café Caturra, Café Típica, Café Borbón, Café Tabí, Maracuyá, Lulo, Cholupa, "
            "Granadilla, Gulupa, Pitahaya Amarilla, Tilapia, Trucha"
        ),
        "precio_referencia": "Precio exportación FOB",
        "email": "",
        "whatsapp": "",
        "sitio_web": "",
    },
]


class Command(BaseCommand):
    help = "Registra los 12 compradores oficiales del Huila. Idempotente."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING("=== seed_compradores_huila: iniciando ===")
        )

        creados = 0
        actualizados = 0

        for datos in COMPRADORES_HUILA:
            comp, created = Comprador.objects.update_or_create(
                nombre=datos["nombre"],
                defaults={
                    "tipo": datos["tipo"],
                    "municipio": datos["municipio"],
                    "contacto": datos["contacto"],
                    "cultivos_interes": datos["cultivos_interes"],
                    "precio_referencia": datos["precio_referencia"] or None,
                    "activo": True,
                    "email": datos["email"],
                    "whatsapp": datos["whatsapp"],
                    "sitio_web": datos["sitio_web"],
                },
            )
            if created:
                creados += 1
                self.stdout.write(f"  [+] Comprador creado: {comp.nombre}")
            else:
                actualizados += 1
                self.stdout.write(f"  [~] Comprador actualizado: {comp.nombre}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nComprador — creados: {creados}, actualizados: {actualizados}"
            )
        )

        total = Comprador.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Total compradores en BD: {total}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS("=== seed_compradores_huila: completado ===")
        )
