from django import forms

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from utils.grace_period import get_allowed_grace_days, is_within_grace
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
    is_billable = models.BooleanField(default=False)

    # Daily Allowance (DA) Details
    da_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_allowance_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_allowance_currency = models.CharField(max_length=10, null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    
    def clean(self):
        """Custom validation for timesheet entry."""

        if not self.time_from or not self.time_to:
            raise ValidationError("Both 'time from' and 'time to' are required.")

        duration = datetime.combine(datetime.today(), self.time_to) - datetime.combine(datetime.today(), self.time_from)
        if duration.total_seconds() > 7200:
            raise ValidationError("Time duration cannot exceed 2 hours.")

        if self.employee_id:
            from utils.grace_period import get_allowed_grace_days, is_within_grace
            grace_days = get_allowed_grace_days(self.employee)
            if not is_within_grace(self.date, grace_days):
                raise ValidationError(
                    f"Submission deadline passed (grace period: {grace_days} days). Contact manager."
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



class CompensatoryOff(models.Model):
    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    date_earned = models.DateField()
    hours_logged = models.DecimalField(max_digits=4, decimal_places=2)
    approved = models.BooleanField(default=False)
    credited_days = models.DecimalField(max_digits=3, decimal_places=1)  # 0.5 or 1.0
    timesheet = models.OneToOneField('timesheet.Timesheet', on_delete=models.CASCADE)

class CompOffBalance(models.Model):
    employee = models.OneToOneField('employee.EmployeeProfile', on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=4, decimal_places=1, default=0.0)

class CompOffApplication(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    date_applied_for = models.DateField()
    number_of_days = models.DecimalField(max_digits=3, decimal_places=1)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')
    ], default='Pending')
    date_requested = models.DateTimeField(auto_now_add=True)  # <-- Newly added
    reason = models.TextField(blank=True, null=True)          # <-- Newly added

    def __str__(self):
        return f"{self.employee.user.username} — {self.date_applied_for} ({self.number_of_days} days)"



#class CompOffApplicationForm(forms.ModelForm):
    #class Meta:
       # model = CompOffApplication
       # fields = ['compoff_date', 'days_requested']
