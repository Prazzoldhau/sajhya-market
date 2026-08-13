from django.apps import AppConfig


class DeliveryAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'delivery_app'

    def ready(self):
        from . import signals  # noqa: F401  -- registers the Order post_save receiver
