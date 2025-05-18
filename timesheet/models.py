from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal

# No direct imports from project/employee/expenses
# Use string-based FK references

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

    da_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_allowance_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_allowance_currency = models.CharField(max_length=10, null=True, blank=True)

    def clean(self):
        if not self.time_from or not self.time_to:
            raise ValidationError("Both 'time from' and 'time to' are required.")

        duration = datetime.combine(datetime.today(), self.time_to) - datetime.combine(datetime.today(), self.time_from)
        if duration.total_seconds() > 7200:
            raise ValidationError("Time duration cannot exceed 2 hours.")

        if self.employee_id:
            from expenses.models import EmployeeExpenseSetting  # imported here to avoid circular imports
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
        if not self.employee_id:
            super().save(*args, **kwargs)
            return

        self.clean()

        # Centralized DA logic
        from project.services.da_calculator import calculate_da
        self.daily_allowance_amount, self.daily_allowance_currency = calculate_da(self)

        super().save(*args, **kwargs)

        from employee.models import AuditLog, LeaveBalance  # Avoid circular import
        AuditLog.objects.create(
            user=self.employee.user,
            action="Timesheet Submitted",
            details=f"Timesheet for {self.project.name} on {self.date}"
        )

        if getattr(self.project, 'location', '') == 'Office':
            same_day_entries = Timesheet.objects.filter(employee=self.employee, date=self.date)
            total_hours = sum([
                (datetime.combine(self.date, e.time_to) - datetime.combine(self.date, e.time_from)).seconds
                for e in same_day_entries
            ]) / 3600

            is_weekend = self.date.weekday() >= 5
            status = 'Absent'
            comp_off = 0

            if total_hours >= 8:
                status = 'Present'
            elif total_hours >= 4:
                status = 'Half Day' if not is_weekend else 'Present'
                comp_off = 1 if is_weekend else 0
            else:
                status = 'Absent' if not is_weekend else 'Half Day'
                comp_off = 0.5 if is_weekend else 0

            Attendance.objects.update_or_create(
                employee=self.employee,
                date=self.date,
                defaults={'status': status}
            )

            if comp_off > 0:
                leave_balance, _ = LeaveBalance.objects.get_or_create(employee=self.employee)
                leave_balance.c_off += comp_off
                leave_balance.save()

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.project.name} ({self.date})"
