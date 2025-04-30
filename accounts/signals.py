# In accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from accounts.models import CustomUser
from employee.models import EmployeeProfile

@receiver(post_save, sender=CustomUser)
def create_employee_profile_and_group(sender, instance, created, **kwargs):
    if created:
        profile, _ = EmployeeProfile.objects.get_or_create(user=instance)
        if profile.role:
            group = Group.objects.filter(name=profile.role).first()
            if group:
                instance.groups.add(group)
