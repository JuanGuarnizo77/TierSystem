"""
Motor Estadístico de Predicción de Tendencia de Precios Agropecuarios.
=====================================================================
Implementa un modelo de regresión lineal simple por el método de mínimos
cuadrados ordinarios (OLS) para proyectar la tendencia a corto plazo
('Alza', 'Baja', 'Estable') y el precio estimado para la semana siguiente.

Diseñado con dependencias mínimas (únicamente la librería estándar `statistics`),
garantizando portabilidad, bajo consumo de memoria y ejecución veloz sin numpy.
"""

import statistics
from typing import List, Dict, Any


# =============================================================================
# Umbrales Estadísticos y Criterios de Clasificación
# =============================================================================
# Una pendiente normalizada de 0.5% semanal acumulada en 7 semanas equivale
# aproximadamente a una variación del 3.5%, cubriendo el umbral de negocio del 3%.
UMBRAL_ALZA = 0.5       # Pendiente > +0.5% por semana → Clasificación: 'Alza'
UMBRAL_BAJA = -0.5      # Pendiente < -0.5% por semana → Clasificación: 'Baja'

# Cantidad mínima y óptima de semanas históricas para cómputo estadístico
MIN_SEMANAS = 3          # Mínimo muestral indispensable para trazar la recta
MAX_SEMANAS_CONFIANZA = 8  # A partir de 8 semanas se alcanza el 100% de confianza estadística


def _regresion_lineal(xs: List[float], ys: List[float]):
    """
    Calcula la recta de mejor ajuste y = m*x + b por mínimos cuadrados ordinarios.

    Fórmulas:
        m = Σ((x_i - x_media) * (y_i - y_media)) / Σ((x_i - x_media)^2)
        b = y_media - m * x_media

    Parámetros:
        xs (List[float]): Índices cronológicos de las semanas (0, 1, ... n-1).
        ys (List[float]): Precios históricos correspondientes a cada semana.

    Retorna:
        tuple[float, float]: Tupla (pendiente m, intercepto b).
    """
    n = len(xs)
    if n < 2:
        return 0.0, statistics.mean(ys) if ys else 0.0

    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)

    # Covarianza muestral y varianza de la variable independiente
    numerador = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    denominador = sum((xs[i] - mean_x) ** 2 for i in range(n))

    # Salvaguarda ante varianza nula (precios perfectamente constantes o un solo valor)
    if denominador == 0:
        return 0.0, mean_y

    m = numerador / denominador
    b = mean_y - m * mean_x
    return m, b


def calcular_prediccion(precios: List[float]) -> Dict[str, Any]:
    """
    Genera el pronóstico econométrico de tendencia y precio para la semana entrante.

    Parámetros:
        precios (List[float]): Serie temporal ordenada cronológicamente (antiguo a reciente).

    Retorna:
        dict: Diccionario estructurado con:
            - `tendencia` (str): 'Alza', 'Baja' o 'Estable'.
            - `confianza_pct` (float): Nivel de confianza entre 0.0% y 100.0%.
            - `precio_estimado` (float): Proyección del valor en COP para x = n.
            - `variacion_pct` (float): Porcentaje de variación proyectado vs última semana.
            - `semanas_usadas` (int): Cantidad de semanas consideradas en el análisis.
    """
    # Si no se alcanza la masa crítica de datos, se asume estabilidad con confianza nula
    if not precios or len(precios) < MIN_SEMANAS:
        return {
            'tendencia': 'Estable',
            'confianza_pct': 0.0,
            'precio_estimado': precios[-1] if precios else 0.0,
            'variacion_pct': 0.0,
            'semanas_usadas': len(precios),
        }

    # Ventana móvil de análisis: se toman como máximo las últimas 16 semanas para captar la dinámica reciente
    datos = precios[-16:]
    n = len(datos)
    xs = list(range(n))
    ys = [float(p) for p in datos]

    # Ajuste de la recta de regresión lineal
    m, b = _regresion_lineal(xs, ys)

    # Proyección lineal para el periodo x = n (siguiente semana en la serie)
    precio_estimado = m * n + b
    ultimo_precio = ys[-1]

    # Normalización de la pendiente relativa al precio promedio
    precio_medio = statistics.mean(ys)
    if precio_medio == 0:
        pendiente_normalizada = 0.0
    else:
        pendiente_normalizada = (m / precio_medio) * 100

    # Clasificación cualitativa de la dirección del mercado
    if pendiente_normalizada > UMBRAL_ALZA:
        tendencia = 'Alza'
    elif pendiente_normalizada < UMBRAL_BAJA:
        tendencia = 'Baja'
    else:
        tendencia = 'Estable'

    # Cálculo del diferencial porcentual proyectado
    if ultimo_precio > 0:
        variacion_pct = ((precio_estimado - ultimo_precio) / ultimo_precio) * 100
    else:
        variacion_pct = 0.0

    # Escalamiento de la confiabilidad estadística según densidad de observaciones
    confianza_pct = min(100.0, (n / MAX_SEMANAS_CONFIANZA) * 100)

    return {
        'tendencia': tendencia,
        'confianza_pct': round(confianza_pct, 1),
        'precio_estimado': round(precio_estimado, 2),
        'variacion_pct': round(variacion_pct, 2),
        'semanas_usadas': n,
    }
