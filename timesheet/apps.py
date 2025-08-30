from django.apps import AppConfig


class TimesheetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "timesheet"

    def ready(self):
        """Place initialization logic here that requires app registry."""
        # No startup logic is required at the moment.
        pass
