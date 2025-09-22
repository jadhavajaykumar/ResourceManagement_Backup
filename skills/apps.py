# skills/apps.py
from django.apps import AppConfig

class SkillsConfig(AppConfig):
    name = 'skills'

    def ready(self):
        try:
            import skills.signals  # noqa
        except Exception:
            pass

