from django.apps import AppConfig


class ExpensesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.expenses"
    verbose_name = "Expenses"

    def ready(self):
        """Import signals when the app is ready."""
        import apps.expenses.signals  # noqa: F401
