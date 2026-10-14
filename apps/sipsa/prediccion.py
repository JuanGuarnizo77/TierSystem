"""
Motor de predicción de tendencia de precios usando regresión lineal simple.
Usa únicamente la librería estándar (statistics) — numpy no es requerido.
"""
import statistics
from typing import List, Dict, Any


# Umbrales para clasificar la pendiente normalizada como Alza/Baja/Estable.
# 0.5 %/semana × 7 semanas ≈ 3.5 % de variación total, lo que cubre el
# criterio de negocio del 3 % establecido en el requerimiento original.
# Se trabaja sobre la pendiente normalizada (% por semana) en lugar de sobre
# la variación acumulada para mantener consistencia independientemente del
# número de semanas históricas disponibles.
UMBRAL_ALZA = 0.5       # pendiente > +0.5% por semana → Alza
UMBRAL_BAJA = -0.5      # pendiente < -0.5% por semana → Baja

# Confianza mínima aceptable (más semanas = más confianza)
MIN_SEMANAS = 3          # mínimo de puntos para calcular
MAX_SEMANAS_CONFIANZA = 8  # a partir de aquí la confianza es máxima


def _regresion_lineal(xs: List[float], ys: List[float]):
    """
    Calcula la pendiente (m) e intercepto (b) de la recta de mínimos cuadrados.
    Devuelve (m, b). Si hay menos de 2 puntos o varianza nula, devuelve (0, media(ys)).
    """
    n = len(xs)
    if n < 2:
        return 0.0, statistics.mean(ys) if ys else 0.0

    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)

    numerador = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denominador = sum((xs[i] - mean_x) ** 2 for i in range(n))

    if denominador == 0:
        return 0.0, mean_y

    m = numerador / denominador
    b = mean_y - m * mean_x
    return m, b


def calcular_prediccion(precios: List[float]) -> Dict[str, Any]:
    """
    Calcula la predicción de tendencia a partir de una lista de precios
    históricos (de más antiguo a más reciente).

    Returns:
        dict con claves:
            - tendencia: 'Alza' | 'Baja' | 'Estable'
            - confianza_pct: float 0-100
            - precio_estimado: float (precio proyectado para siguiente semana)
            - variacion_pct: float (variación % respecto al último precio)
            - semanas_usadas: int
    """
    if not precios or len(precios) < MIN_SEMANAS:
        return {
            'tendencia': 'Estable',
            'confianza_pct': 0.0,
            'precio_estimado': precios[-1] if precios else 0.0,
            'variacion_pct': 0.0,
            'semanas_usadas': len(precios),
        }

    # Usar las últimas MAX_SEMANAS_CONFIANZA*2 semanas como máximo
    datos = precios[-16:]  # últimas 16 semanas máximo
    n = len(datos)
    xs = list(range(n))
    ys = [float(p) for p in datos]

    m, b = _regresion_lineal(xs, ys)

    # Precio estimado para la siguiente semana (x = n)
    precio_estimado = m * n + b
    ultimo_precio = ys[-1]

    # Variación porcentual de la pendiente normalizada por el precio medio
    precio_medio = statistics.mean(ys)
    if precio_medio == 0:
        pendiente_normalizada = 0.0
    else:
        pendiente_normalizada = (m / precio_medio) * 100  # % por semana

    # Clasificar tendencia
    if pendiente_normalizada > UMBRAL_ALZA:
        tendencia = 'Alza'
    elif pendiente_normalizada < UMBRAL_BAJA:
        tendencia = 'Baja'
    else:
        tendencia = 'Estable'

    # Variación % entre último precio real y precio estimado
    if ultimo_precio > 0:
        variacion_pct = ((precio_estimado - ultimo_precio) / ultimo_precio) * 100
    else:
        variacion_pct = 0.0

    # Confianza: escala lineal según cantidad de semanas históricas
    confianza_pct = min(100.0, (n / MAX_SEMANAS_CONFIANZA) * 100)

    return {
        'tendencia': tendencia,
        'confianza_pct': round(confianza_pct, 1),
        'precio_estimado': round(precio_estimado, 2),
        'variacion_pct': round(variacion_pct, 2),
        'semanas_usadas': n,
    }
