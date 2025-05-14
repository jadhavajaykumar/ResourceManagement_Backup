from django.db.models.signals import post_save
from django.dispatch import receiver
from timesheet.models import Timesheet
from expenses.models import DailyAllowance
from datetime import timedelta
from django.utils import timezone

@receiver(post_save, sender=Timesheet)
def create_or_update_da(sender, instance, created, **kwargs):
    if not created:
        return

    project = instance.project
    employee = instance.employee
    date = instance.date

    da_amount = 0
    currency = 'INR'
    is_extended = False

    # Local Project
    if project.location == 'Local':
        if instance.total_hours >= 6:
            da_amount = 300

    # Domestic Project
    elif project.location == 'Domestic':
        da_amount = 600
        continuous_days = Timesheet.objects.filter(
            employee=employee,
            project=project,
            date__lte=date,
            date__gte=date - timedelta(days=59)
        ).count()

        if continuous_days >= 60:
            da_amount += 150
            is_extended = True

    # International
    elif project.location == 'International' and project.da_rate_per_hour:
        da_amount = float(instance.total_hours) * float(project.da_rate_per_hour)
        currency = project.da_currency or 'USD'

    if da_amount > 0:
        DailyAllowance.objects.update_or_create(
            timesheet=instance,
            defaults={
                'employee': employee,
                'project': project,
                'date': date,
                'da_amount': da_amount,
                'currency': currency,
                'is_extended': is_extended
            }
        )
