# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from employee.models import EmployeeProfile

@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'Manager' if instance.is_staff else instance.role
        EmployeeProfile.objects.create(user=instance, role=role)       
        
        