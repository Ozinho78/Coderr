from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_app'

    def ready(self):
        # wird beim Start geladen -> importiert unsere Signal-Handler
        from . import signals  # noqa: F401  # nur Import, kein direkter Zugriff