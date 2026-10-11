from django.apps import AppConfig


class CerrosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cerros'

    def ready(self):
        from django.db.models.signals import post_migrate

        from . import signals  # noqa: F401  (registers the receivers)
        from .roles import ensure_roles

        post_migrate.connect(ensure_roles, sender=self)
