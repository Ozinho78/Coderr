from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    """Starts App and imports signals handler"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_app'

    def ready(self):
        from . import signals