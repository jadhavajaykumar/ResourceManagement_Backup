from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal

from employee.models import EmployeeProfile, AuditLog, LeaveBalance
from project.models import Project, Task
from expenses.models import EmployeeExpenseSetting


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Half Day', 'Half Day'),
        ('Absent', 'Absent'),
    ]
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
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

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='timesheets')
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    time_from = models.TimeField()
    time_to = models.TimeField()
    task_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_locked = models.BooleanField(default=False)

    # DA fields
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
            setting = EmployeeExpenseSetting.objects.filter(employee=self.employee).first()
            grace_period = setting.grace_days if setting else 3
            override = setting.allow_submission_override if setting else False

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

        # ----------------- DA Logic -------------------
        total_hours = (datetime.combine(datetime.today(), self.time_to) -
                       datetime.combine(datetime.today(), self.time_from)).total_seconds() / 3600

        self.daily_allowance_amount = None
        self.daily_allowance_currency = None

        if self.project.location == 'Local':
            if total_hours >= 6:
                self.daily_allowance_amount = Decimal(300)
                self.daily_allowance_currency = 'INR'

        elif self.project.location == 'Domestic':
            last_60_days = Timesheet.objects.filter(
                employee=self.employee,
                project=self.project,
                date__lte=self.date,
                date__gte=self.date - timedelta(days=59)
            ).values_list('date', flat=True)

            continuous_days = set(last_60_days)
            total_streak = sum(
                1 for i in range(60)
                if (self.date - timedelta(days=i)) in continuous_days
            )

            self.daily_allowance_amount = Decimal(750 if total_streak == 60 else 600)
            self.daily_allowance_currency = 'INR'

        elif self.project.location == 'International' and self.project.country_rate:
            da_rate = self.project.country_rate.da_rate_per_hour
            currency = self.project.country_rate.currency
            self.daily_allowance_amount = Decimal(total_hours) * da_rate
            self.daily_allowance_currency = currency

        elif self.project.location == 'Office':
            self.daily_allowance_amount = None
            self.daily_allowance_currency = None

        super().save(*args, **kwargs)

        # ----------------- Audit Log -------------------
        AuditLog.objects.create(
            user=self.employee.user,
            action="Timesheet Submitted",
            details=f"Timesheet for {self.project.name} on {self.date}"
        )

        # ----------------- Attendance for 'Office' Projects -------------------
        if self.project.location == 'Office':
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
                leave_balance.compensatory_off += comp_off
                leave_balance.save()

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.project.name} ({self.date})"
