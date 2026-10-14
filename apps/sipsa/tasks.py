def actualizar_sipsa_semanal():
    """Función para llamar desde scheduler (celery beat, django-cron, o cron del SO)."""
    from django.core.management import call_command
    call_command('actualizar_sipsa')
