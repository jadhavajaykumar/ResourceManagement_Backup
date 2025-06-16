from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    middle_name = models.CharField(max_length=50, blank=True, null=True)

    @property
    def role(self):
        if hasattr(self, 'employeeprofile'):
            return self.employeeprofile.role
        return 'Unknown'


    class Meta:
        permissions = [
            ("manage_employees", "Can manage employee roles"),
            ("manage_managers", "Can manage manager roles"),
            ("manage_hr", "Can manage HR roles"),
        ]
