from django.apps import AppConfig

class JobcardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jobcards"

    def ready(self):
        # Carrega os signals quando o app inicia
        from importlib import import_module
        import_module("jobcards.signals")
