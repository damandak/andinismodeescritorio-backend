from django.apps import AppConfig


class CerrosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cerros'

    def ready(self):
        from . import signals  # noqa: F401  (registers the receivers)
