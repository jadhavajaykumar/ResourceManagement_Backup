from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal

# timesheet/models.py


from employee.models import EmployeeProfile
from project.models import Task


# Avoid direct model imports from related apps in class body
# Use string-based references to prevent circular imports

class Meta:
    db_table = 'employee_timesheetentry'
    managed = True



class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Half Day', 'Half Day'),
        ('Absent', 'Absent'),
    ]

    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    added_c_off = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)

    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.date} - {self.status}"


class Timesheet(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE, related_name='timesheets')
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE)
    task = models.ForeignKey('project.Task', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    time_from = models.TimeField()
    time_to = models.TimeField()
    task_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_locked = models.BooleanField(default=False)

    # Daily Allowance (DA) Details
    da_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_allowance_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_allowance_currency = models.CharField(max_length=10, null=True, blank=True)

    def clean(self):
        """Custom validation for timesheet entry."""
        if not self.time_from or not self.time_to:
            raise ValidationError("Both 'time from' and 'time to' are required.")

        duration = datetime.combine(datetime.today(), self.time_to) - datetime.combine(datetime.today(), self.time_from)
        if duration.total_seconds() > 7200:
            raise ValidationError("Time duration cannot exceed 2 hours.")

        if self.employee_id:
            from expenses.models import EmployeeExpenseSetting  # local import to prevent circular reference
            setting = EmployeeExpenseSetting.objects.filter(employee=self.employee).first()
            grace_period = setting.grace_period_days if setting else 3
            override = getattr(setting, 'allow_submission_override', False)

            if not override:
                today = datetime.today().date()
                last_allowed = self.date + timedelta(days=grace_period)
                if today > last_allowed:
                    raise ValidationError(
                        f"Submission deadline passed (grace period: {grace_period} days). Contact manager."
                    )

    def save(self, *args, **kwargs):
        """Delegates logic to service before saving."""
        if not self.employee_id:
            super().save(*args, **kwargs)
            return

        self.clean()

        from timesheet.services.timesheet_service import process_timesheet_save
        process_timesheet_save(self)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.project.name} ({self.date})"


class TimesheetEntry(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    details = models.TextField()

    def save(self, *args, **kwargs):
        if not self.details:
            self.details = f"Timesheet for {self.task.project.name if self.task else ''} on {self.date}"
        super().save(*args, **kwargs)

