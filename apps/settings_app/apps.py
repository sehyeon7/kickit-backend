from django.apps import AppConfig


class SettingsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.settings_app'

    def ready(self):
        import apps.settings_app.signals
