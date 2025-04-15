from django.db import models
from django.utils import timezone
from employee.models import EmployeeProfile, AuditLog
from project.models import Project, Task

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
        from django.core.exceptions import ValidationError
        from datetime import timedelta, datetime

        time_format = '%H:%M:%S'
        time1 = datetime.strptime(str(self.time_from), time_format)
        time2 = datetime.strptime(str(self.time_to), time_format)
        duration = time2 - time1
        if duration > timedelta(hours=2):
            raise ValidationError("Timeslot cannot be more than 2 hours.")

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
