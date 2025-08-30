from django.db import models
from django.contrib.auth.models import Group


class ModuleAccess(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    module = models.CharField(max_length=100)

    class Meta:
        unique_together = ('group', 'module')
        verbose_name = 'Module Access'
        verbose_name_plural = 'Module Accesses'

    def __str__(self):
        return f"{self.group.name} -> {self.module}"