from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid

def generate_employee_id():
    return f"EMP-{uuid.uuid4().hex[:6].upper()}"

class EmployeeProfile(models.Model):
    ROLES = (
        ('Employee', 'Employee'),
        ('Manager', 'Manager'),
        ('HR', 'HR'),
        ('Accountant', 'Accountant'),
        ('Director', 'Director'),
        ('Admin', 'Admin'),
    )
    EMPLOYMENT_TYPES = [
        ('Permanent', 'Permanent'),
        ('Contract', 'Contract'),
        ('Intern', 'Intern'),
    ]
    user = models.OneToOneField('accounts.CustomUser', on_delete=models.CASCADE, related_name='employeeprofile')
    role = models.CharField(max_length=20, choices=ROLES, default='Employee')
    career_start_date = models.DateField(null=True, blank=True)
    probotix_joining_date = models.DateField(default=timezone.now)
    confirmation_date = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    contact_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)
    emergency_contact_number = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=20, unique=True, default=generate_employee_id)
    department = models.CharField(max_length=50, blank=True)
    reporting_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_employees')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='Permanent')
    pan_aadhar_ssn = models.CharField(max_length=20, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_ifsc_code = models.CharField(max_length=20, blank=True)
    epf_number = models.CharField(max_length=20, blank=True)
    grace_period_days = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

    def save(self, *args, **kwargs):
        if not self.confirmation_date and self.probotix_joining_date:
            self.confirmation_date = self.probotix_joining_date + timedelta(days=180)
        super().save(*args, **kwargs)
        AuditLog.objects.create(
            user=self.user,
            action='Updated Employee Profile',
            details=f"Profile for {self.employee_id} updated"
        )

    @property
    def total_experience(self):
        if self.career_start_date:
            today = timezone.now().date()
            return today.year - self.career_start_date.year - (
                (today.month, today.day) < (self.career_start_date.month, self.career_start_date.day)
            )
        return None

    @property
    def confirmation_due_today(self):
        return self.confirmation_date == timezone.now().date()

class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"



class LeaveBalance(models.Model):
    employee = models.OneToOneField('employee.EmployeeProfile', on_delete=models.CASCADE, related_name='leave_balance')
    c_off = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - C-Off: {self.c_off}"
