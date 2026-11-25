"""
Módulo de Utilidades Transversales y Controles de Seguridad de TierSystem.
==========================================================================
Proporciona funciones auxiliares de uso compartido para:
  1. Sanitización contra inyección de fórmulas en hojas de cálculo (CSV/Excel Injection - CWE-1236).
  2. Extracción segura de dirección IP del cliente para trazabilidad y control de abuso.
  3. Limitación de tasa de peticiones (Rate Limiting) respaldada por caché de Django.
  4. Registro estructurado de eventos de auditoría y seguridad sin exposición de secretos.
  5. Validación y normalización en servidor de geometrías GeoJSON de terrenos.
"""

import json
import logging
import math
from django.core.cache import cache

security_logger = logging.getLogger('tiersystem.security')

# Prefijos peligrosos que Microsoft Excel, LibreOffice Calc o Google Sheets interpretan como fórmulas ejecutables
PREFIJOS_FORMULA_EXCEL = ('=', '+', '-', '@', '\t', '\r')


def sanitizar_celda_excel(valor):
    """
    Previene ataques de Inyección de Fórmulas en Excel / CSV (CWE-1236 / OWASP).

    Si el valor es una cadena de texto que comienza con caracteres de invocación
    de fórmulas ('=', '+', '-', '@', tabulador o retorno de carro), antepone
    una comilla simple (') para forzar su interpretación literal como texto plano.
    No altera valores numéricos (int, float, Decimal).
    """
    if valor is None:
        return ''
    if isinstance(valor, (int, float)):
        return valor
    texto = str(valor)
    if texto.startswith(PREFIJOS_FORMULA_EXCEL):
        return f"'{texto}"
    return texto


def validar_y_normalizar_poligono(coordenadas_raw):
    """
    Valida en el servidor que `coordenadas_poligono` sea un JSON/GeoJSON geométrico válido
    y lo re-serializa de forma segura (previniendo Stored XSS e inyección de payloads arbitrarios).

    Retorna:
      `(es_valido: bool, resultado_o_error: str | None)`
    """
    if coordenadas_raw is None:
        return True, None
    texto = str(coordenadas_raw).strip()
    if not texto:
        return True, ''
    if len(texto) > 65536:
        return False, 'El polígono geográfico excede el tamaño máximo permitido.'

    try:
        parsed = json.loads(texto)
    except (ValueError, TypeError):
        return False, 'Las coordenadas del polígono deben tener un formato GeoJSON/JSON válido.'

    def _contiene_coordenadas_validas(nodo, profundidad=0):
        if profundidad > 10:
            return False
        if isinstance(nodo, (int, float)) and not isinstance(nodo, bool):
            return not (math.isnan(nodo) or math.isinf(nodo)) and -180.0 <= float(nodo) <= 180.0
        if isinstance(nodo, list):
            if not nodo or len(nodo) > 2000:
                return False
            return all(_contiene_coordenadas_validas(item, profundidad + 1) for item in nodo)
        if isinstance(nodo, dict):
            if 'lat' in nodo and ('lng' in nodo or 'lon' in nodo):
                lat = nodo.get('lat')
                lon = nodo.get('lng', nodo.get('lon'))
                return (
                    isinstance(lat, (int, float)) and not isinstance(lat, bool)
                    and isinstance(lon, (int, float)) and not isinstance(lon, bool)
                    and not (math.isnan(lat) or math.isinf(lat) or math.isnan(lon) or math.isinf(lon))
                    and -90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0
                )
        return False

    if isinstance(parsed, dict):
        tipo = parsed.get('type')
        if tipo == 'Feature':
            geom = parsed.get('geometry')
            if not isinstance(geom, dict) or geom.get('type') not in ('Polygon', 'MultiPolygon', 'Point', 'LineString'):
                return False, 'La geometría GeoJSON del terreno no es válida.'
            coords = geom.get('coordinates')
            if not _contiene_coordenadas_validas(coords):
                return False, 'Las coordenadas geográficas del polígono están fuera de rango.'
            limpio = {
                'type': 'Feature',
                'properties': {},
                'geometry': {
                    'type': geom.get('type'),
                    'coordinates': coords,
                },
            }
        elif tipo in ('Polygon', 'MultiPolygon'):
            coords = parsed.get('coordinates')
            if not _contiene_coordenadas_validas(coords):
                return False, 'Las coordenadas geográficas del polígono están fuera de rango.'
            limpio = {
                'type': tipo,
                'coordinates': coords,
            }
        elif tipo == 'FeatureCollection' and isinstance(parsed.get('features'), list) and parsed['features']:
            primera = parsed['features'][0]
            if not isinstance(primera, dict):
                return False, 'Colección GeoJSON inválida.'
            return validar_y_normalizar_poligono(json.dumps(primera))
        else:
            return False, 'Estructura GeoJSON de polígono no reconocida.'
    elif isinstance(parsed, list):
        if not _contiene_coordenadas_validas(parsed):
            return False, 'Lista de coordenadas geográficas inválida o fuera de rango.'
        limpio = parsed
    else:
        return False, 'Formato de coordenadas de polígono inválido.'

    serializado = json.dumps(limpio, ensure_ascii=True).replace('</', '<\\/')
    return True, serializado


def obtener_ip_cliente(request):
    """
    Obtiene la dirección IP de origen de la solicitud HTTP de forma segura.
    Prioriza el primer salto de X-Forwarded-For cuando opera detrás de un proxy inverso confiable.
    """
    if request is None or not hasattr(request, 'META'):
        return '0.0.0.0'
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0') or '0.0.0.0'


def registrar_evento_seguridad(evento_o_request, request=None, detalle_pos='', nivel='INFO', detalle='', usuario=None):
    """
    Registra un evento en el log de auditoría de seguridad (tiersystem.security).

    Soporta tanto la firma `(evento, request=..., nivel=..., detalle=...)` como
    `(request, evento, detalle, nivel=...)`.

    Cumple con OWASP ASVS V7 / ISO 27002:
      - Identifica quién realizó la acción, desde qué IP y el resultado.
      - Jamás almacena contraseñas, tokens ni secretos criptográficos.
    """
    if isinstance(evento_o_request, str):
        evento = evento_o_request
        req = request
        texto_detalle = detalle or (detalle_pos if isinstance(detalle_pos, str) else '')
    else:
        req = evento_o_request
        evento = request if isinstance(request, str) else 'EVENTO_SEGURIDAD'
        texto_detalle = detalle or (detalle_pos if isinstance(detalle_pos, str) else '')

    ip = obtener_ip_cliente(req) if req is not None else 'N/A'
    if usuario is None and req is not None and hasattr(request_obj := req, 'user') and getattr(request_obj.user, 'is_authenticated', False):
        usuario_str = f"{request_obj.user.username} (id={request_obj.user.id})"
    elif usuario is not None:
        usuario_str = str(usuario)
    else:
        usuario_str = 'anonimo'

    mensaje = f"[EVENTO={evento}] [USUARIO={usuario_str}] [IP={ip}] {texto_detalle}".strip()
    log_fn = getattr(security_logger, nivel.lower(), security_logger.info)
    log_fn(mensaje)


def verificar_rate_limit(
    request,
    scope,
    max_requests=10,
    window_seconds=60,
    identificador_extra='',
    limite=None,
    ventana_segundos=None,
):
    """
    Verifica e incrementa un contador de límite de peticiones (Rate Limiting) en caché.

    Si se invoca con `max_requests` / `window_seconds`, retorna `bool` (True = permitido, False = bloqueado).
    Si se invoca con `limite` / `ventana_segundos`, retorna la tupla `(bloqueado: bool, restantes: int)`.
    """
    modo_tupla = (limite is not None) or (ventana_segundos is not None)
    tope = limite if limite is not None else max_requests
    ventana = ventana_segundos if ventana_segundos is not None else window_seconds

    ip = obtener_ip_cliente(request)
    user_part = (
        f"u:{request.user.id}"
        if (hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False))
        else f"ip:{ip}"
    )
    extra = f":{identificador_extra}" if identificador_extra else ""
    cache_key = f"rl:{scope}:{user_part}{extra}"

    intentos = cache.get(cache_key, 0)
    if intentos >= tope:
        registrar_evento_seguridad(
            'RATE_LIMIT_EXCEEDED',
            request=request,
            nivel='WARNING',
            detalle=f"Scope '{scope}' superó {tope} peticiones en {ventana}s.",
        )
        return (True, 0) if modo_tupla else False

    nuevos_intentos = intentos + 1
    if intentos == 0:
        cache.set(cache_key, 1, timeout=ventana)
    else:
        try:
            cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, nuevos_intentos, timeout=ventana)

    return (False, max(0, tope - nuevos_intentos)) if modo_tupla else True


def limpiar_rate_limit(request, scope, identificador_extra=''):
    """Reinicia el contador de intentos tras una operación autenticada exitosa."""
    ip = obtener_ip_cliente(request)
    user_part = (
        f"u:{request.user.id}"
        if (hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False))
        else f"ip:{ip}"
    )
    extra = f":{identificador_extra}" if identificador_extra else ""
    cache_key = f"rl:{scope}:{user_part}{extra}"
    cache.delete(cache_key)
