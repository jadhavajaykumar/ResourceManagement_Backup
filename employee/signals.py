from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import EmployeeProfile

@receiver(post_save, sender=get_user_model())
def create_employee_profile(sender, instance, created, **kwargs):
    """Automatically create EmployeeProfile when new User is created"""
    if created:
        EmployeeProfile.objects.get_or_create(
            user=instance,
            defaults={'role': 'Employee'}  # Default role
        )