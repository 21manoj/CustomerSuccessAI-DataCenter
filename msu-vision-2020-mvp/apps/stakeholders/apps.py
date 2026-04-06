from django.apps import AppConfig


class StakeholdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stakeholders"
    label = "stakeholders"
    verbose_name = "Stakeholders"

    def ready(self):
        import apps.stakeholders.signals  # noqa: F401
