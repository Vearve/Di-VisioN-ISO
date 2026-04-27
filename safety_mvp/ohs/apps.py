from django.apps import AppConfig


class OhsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'safety_mvp.ohs'

    def ready(self):
        from . import signals  # noqa: F401
