"""
Función para llamar desde un scheduler externo (cron del SO, Celery Beat, etc.).

Configuración cron (lunes 07:00 AM hora Colombia):
    0 7 * * 1 /ruta/venv/bin/python /ruta/manage.py actualizar_sipsa >> /var/log/sipsa.log 2>&1

En Windows (desarrollo), usar el Programador de Tareas de Windows
apuntando al mismo comando semanalmente.
"""


def actualizar_sipsa_semanal():
    """Punto de entrada para scheduler externo."""
    from django.core.management import call_command
    call_command('actualizar_sipsa')
