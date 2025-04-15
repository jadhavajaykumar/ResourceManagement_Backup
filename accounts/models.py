from django.contrib.auth.models import AbstractUser
from django.db import models

  

class CustomUser(AbstractUser):
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    
    # Remove the role field since we're using EmployeeProfile
    # ... keep other fields ...
    
    @property
    def role(self):
        """Backward-compatible role accessor"""
        try:
            return self.employee_profile.role
        except AttributeError:
            return 'Employee'
            
            
    class Meta:
        permissions = [
            ("manage_employees", "Can manage employee roles"),
            ("manage_managers", "Can manage manager roles"),
            ("manage_hr", "Can manage HR roles"),
        ]