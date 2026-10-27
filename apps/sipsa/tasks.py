"""
Tareas Programadas Periódicas para el Módulo SIPSA.
===================================================
Define los puntos de entrada para planificadores de tareas en segundo plano
(Celery Beat, django-crontab, cron de Linux o APScheduler) para ejecutar la
actualización semanal automática de precios agropecuarios.
"""

from django.core.management import call_command


def actualizar_sipsa_semanal():
    """
    Tarea programada para ingesta periódica de precios SIPSA/DANE.

    Invoca el comando `actualizar_sipsa` para consultar los boletines del DANE
    y refrescar las cotizaciones oficiales de las centrales de abastos.
    """
    call_command('actualizar_sipsa')
