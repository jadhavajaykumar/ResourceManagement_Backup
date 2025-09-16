
# approvals/apps.py
from django.apps import AppConfig

class ApprovalsConfig(AppConfig):
    name = 'approvals'

    def ready(self):
        # import signals so they are registered
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
