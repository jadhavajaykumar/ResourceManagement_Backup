from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from utils.grace_period import get_allowed_grace_days, is_within_grace
from employee.models import EmployeeProfile
from project.models import Task, Project

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
        
        

   
     

class TimeSlot(models.Model):
    """Represents a time slot within a shift"""
    timesheet = models.ForeignKey('Timesheet', on_delete=models.CASCADE, related_name='time_slots')
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE,null=True, blank=True, related_name="timeslots")
    date = models.DateField(null=True, blank=True)
    time_from = models.TimeField()
    time_to = models.TimeField()
    #project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    slot_date = models.DateField(null=True, blank=True)
    class Meta:
        ordering = ['time_from']

    def clean(self):
        if self.time_from is None or self.time_to is None:
            return  # skip validation if values are missing

        if self.time_to <= self.time_from:
            raise ValidationError("End time must be after start time.")
            
    def get_duration_hours(self):
        start = datetime.combine(datetime.today(), self.time_from)
        end = datetime.combine(datetime.today(), self.time_to)
        if self.time_to <= self.time_from:
            end += timedelta(days=1)
        return (end - start).total_seconds() / 3600        

class Timesheet(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='timesheets')
    date = models.DateField(default=timezone.now)
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_locked = models.BooleanField(default=False)
    is_billable = models.BooleanField(default=False)
    da_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_allowance_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_allowance_currency = models.CharField(max_length=10, null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)

    def get_total_hours(self):
        """
        Calculate total shift hours including overnight
        Always uses time slots if available, otherwise calculates from shift times
        """
        # Safe for unsaved instances
        if not self.pk:
            return 0.0
            
        if self.time_slots.exists():
            return sum(float(slot.hours) for slot in self.time_slots.all())
        
        # Fallback to shift times calculation
        start = datetime.combine(self.date, self.shift_start)
        end = datetime.combine(
            self.date + timedelta(days=1) if self.shift_end <= self.shift_start else self.date,
            self.shift_end
        )
        return round((end - start).total_seconds() / 3600, 2)

    def clean(self):
        """Validate the shift times"""
        if self.shift_start == self.shift_end:
            raise ValidationError("Shift cannot have identical start and end times")
        
        # Only validate total hours if instance is saved
        if self.pk:
            total_hours = self.get_total_hours()
            if total_hours > 24:
                raise ValidationError("Shift cannot exceed 24 hours")

    def save(self, *args, **kwargs):
        # Only run clean if instance has primary key
        if self.pk:
            self.clean()
        super().save(*args, **kwargs)

class CompensatoryOff(models.Model):
    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    date_earned = models.DateField()
    hours_logged = models.DecimalField(max_digits=4, decimal_places=2)
    approved = models.BooleanField(default=False)
    credited_days = models.DecimalField(max_digits=3, decimal_places=1)
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
    date_requested = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.employee.user.username} — {self.date_applied_for} ({self.number_of_days} days)"