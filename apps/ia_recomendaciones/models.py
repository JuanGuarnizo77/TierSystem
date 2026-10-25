"""
Modelo de Configuración Global del Sistema y Parámetros de Inferencia IA.
========================================================================
Define el modelo singleton `ConfiguracionGlobal` (US-0038, US-0039), que
centraliza los parámetros operativos del motor de inteligencia artificial y
los límites físicos de calibración de los sensores edafológicos en campo.

Garantiza la consistencia del sistema forzando una única instancia (`pk=1`),
permitiendo a los administradores ajustar tiempos de espera de la API de Gemini
y definir la política de contingencia ante cortes de conectividad.
"""

from django.db import models


class ConfiguracionGlobal(models.Model):
    """
    Configuración centralizada y singleton para el comportamiento de la IA y telemetría.

    Atributos:
        tiempo_espera_ia (IntegerField): Timeout máximo en segundos antes de abortar
                                        la petición HTTP a la API de Google Gemini.
        accion_fallo_ia (CharField): Estrategia de degradación elegante ante fallo de IA:
                                    - 'DB_LOCAL': Conmuta al motor edafológico determinista.
                                    - 'CANCELAR': Cancela la operación notificando al usuario.
        rango_* (FloatField): Umbrales de plausibilidad física para el hardware de sensado,
                              previniendo la ingesta de valores anómalos o lecturas corruptas.
    """
    # US-0039: Política de Gobernanza y Resiliencia de la IA
    tiempo_espera_ia = models.IntegerField(
        default=30,
        help_text="Tiempo máximo de espera para la respuesta del modelo generativo (segundos)"
    )
    accion_fallo_ia = models.CharField(
        max_length=50,
        choices=[
            ('DB_LOCAL', 'Usar base de datos local automáticamente'),
            ('CANCELAR', 'Notificar al usuario y cancelar el análisis')
        ],
        default='DB_LOCAL',
        help_text="Mecanismo de contingencia cuando la API externa no responde"
    )

    # US-0038: Rangos Globales de Validación Fisiográfica y Edafológica de Sensores
    rango_ph_min = models.FloatField(default=0.0, help_text="Límite inferior de pH admisible")
    rango_ph_max = models.FloatField(default=14.0, help_text="Límite superior de pH admisible")

    rango_n_min = models.FloatField(default=0.0, help_text="Nitrógeno mínimo (mg/kg)")
    rango_n_max = models.FloatField(default=1000.0, help_text="Nitrógeno máximo (mg/kg)")

    rango_p_min = models.FloatField(default=0.0, help_text="Fósforo mínimo (mg/kg)")
    rango_p_max = models.FloatField(default=1000.0, help_text="Fósforo máximo (mg/kg)")

    rango_k_min = models.FloatField(default=0.0, help_text="Potasio mínimo (mg/kg)")
    rango_k_max = models.FloatField(default=1000.0, help_text="Potasio máximo (mg/kg)")

    rango_humedad_min = models.FloatField(default=0.0, help_text="Humedad mínima admisible (%)")
    rango_humedad_max = models.FloatField(default=100.0, help_text="Humedad máxima admisible (%)")

    rango_ce_min = models.FloatField(default=0.0, help_text="Conductividad eléctrica mínima (dS/m)")
    rango_ce_max = models.FloatField(default=20.0, help_text="Conductividad eléctrica máxima (dS/m)")

    rango_temp_min = models.FloatField(default=-10.0, help_text="Temperatura mínima edáfica (°C)")
    rango_temp_max = models.FloatField(default=60.0, help_text="Temperatura máxima edáfica (°C)")

    class Meta:
        verbose_name = 'Configuración Global'
        verbose_name_plural = 'Configuraciones Globales'

    def save(self, *args, **kwargs):
        """
        Patrón Singleton: Fuerza que la clave primaria sea siempre 1.

        Previene la creación de múltiples registros de configuración en la tabla,
        asegurando una única fuente de verdad para todo el ecosistema.
        """
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """
        Método de acceso de fábrica que retorna o inicializa la configuración única.

        Retorna:
            ConfiguracionGlobal: La instancia singleton con pk=1.
        """
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        """Identificador textual de la configuración."""
        return "Configuración Global del Sistema"
