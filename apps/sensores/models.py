"""
Modelo de Dominio: Buffer de Telemetría IoT de Sensores Edafológicos.
====================================================================
Define la entidad `LecturaSensor`, utilizada como cola o buffer temporal en
base de datos para recibir las tramas de telemetría transmitidas por microcontroladores
ESP32 conectados mediante transceptores RS485 (protocolo Modbus RTU) a sondas N-P-K 7 en 1.

Estas lecturas brutas son posteriormente estabilizadas mediante análisis estadístico
(cálculo de moda y mediana) para eliminar el ruido eléctrico transitorio antes
de consolidar la medición en un punto de muestreo georreferenciado.
"""

from django.db import models


class LecturaSensor(models.Model):
    """
    Registro individual de telemetría sin procesar proveniente de la sonda de suelo.

    Atributos:
        humedad (FloatField): Humedad relativa volumétrica del suelo desescalada en %.
        temperatura (FloatField): Temperatura del perfil edáfico en grados Celsius (°C).
        conductividad (FloatField): Conductividad eléctrica en µS/cm o dS/m.
        ph (FloatField): Potencial de hidrógeno desescalado (0.0 - 14.0).
        nitrogeno (FloatField): Concentración de nitrógeno disponible en mg/kg.
        fosforo (FloatField): Concentración de fósforo disponible en mg/kg.
        potasio (FloatField): Concentración de potasio disponible en mg/kg.
        timestamp (DateTimeField): Marca temporal precisa de ingesta en el servidor,
                                  fundamental para las ventanas de estabilización de 15 segundos.
    """
    humedad = models.FloatField(null=True, blank=True, help_text="Porcentaje de humedad del suelo (%)")
    temperatura = models.FloatField(null=True, blank=True, help_text="Temperatura del suelo (°C)")
    conductividad = models.FloatField(null=True, blank=True, help_text="Conductividad eléctrica (salinidad)")
    ph = models.FloatField(null=True, blank=True, help_text="Potencial de hidrógeno (pH)")
    nitrogeno = models.FloatField(null=True, blank=True, help_text="Nitrógeno elemental (mg/kg)")
    fosforo = models.FloatField(null=True, blank=True, help_text="Fósforo elemental (mg/kg)")
    potasio = models.FloatField(null=True, blank=True, help_text="Potasio elemental (mg/kg)")
    bateria = models.FloatField(null=True, blank=True, default=None, help_text="Nivel de batería del nodo sensor IoT (%)")
    senal_rssi = models.IntegerField(null=True, blank=True, default=None, help_text="Intensidad de señal inalámbrica RSSI (dBm)")

    # Marca temporal de ingesta automática para ventanas móviles de estabilización
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Instante de recepción de la trama por la API"
    )

    def __str__(self):
        """Identificador textual de la lectura con estampa temporal legible."""
        return f"Lectura {self.id} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
