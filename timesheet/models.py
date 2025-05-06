from django.db import models
from django.utils import timezone
from employee.models import EmployeeProfile, AuditLog
from project.models import Project, Task
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from expenses.models import EmployeeExpenseSetting  # or your correct model

class Timesheet(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='timesheets')
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    time_from = models.TimeField()
    time_to = models.TimeField()
    task_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    da_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

   

    

    def clean(self):
        if not self.time_from or not self.time_to:
            raise ValidationError("Both 'time from' and 'time to' are required.")

        # 1. Check duration ≤ 2 hours
        if self.time_from and self.time_to:
            duration = datetime.combine(datetime.today(), self.time_to) - datetime.combine(datetime.today(), self.time_from)
            if duration.total_seconds() > 7200:
                raise ValidationError("Time duration cannot exceed 2 hours.")

        # 2. Check grace period (skip for manager override)
        setting = EmployeeExpenseSetting.objects.filter(employee=self.employee).first()
        if setting:
            grace_period = setting.grace_days or 0
            override = setting.allow_submission_override
        else:
            grace_period = 0
            override = False

        if not override:
            today = datetime.today().date()
            last_allowed = self.date + timedelta(days=grace_period)
            if today > last_allowed:
                raise ValidationError(f"Submission deadline passed (grace period: {grace_period} days). Contact manager.")



    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        AuditLog.objects.create(
            user=self.employee.user,
            action="Timesheet Submitted",
            details=f"Timesheet for {self.project.name} on {self.date}"
        )

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.project.name} ({self.date})"
