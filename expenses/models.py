from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model
# expenses/models.py

from django.db import models
from employee.models import EmployeeProfile

User = get_user_model()

class ExpenseType(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    name = models.CharField(max_length=50, unique=True)
    requires_kilometers = models.BooleanField(default=False)
    requires_receipt = models.BooleanField(default=False)
    rate_per_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Forwarded to Manager', 'Forwarded to Manager'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    FINAL_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    EXPENSE_TYPE_CHOICES = [
        ('travel-bike', 'Travel - Bike'),
        ('travel-personal-car', 'Travel - Personal Car'),
        ('travel-public', 'Travel - Public Transport'),
        ('travel-cab', 'Travel - Cab'),
        ('other', 'Other'),
    ]

    new_expense_type = models.ForeignKey(
        'ExpenseType',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE)
    date = models.DateField()
    kilometers = models.PositiveIntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    comments = models.TextField(blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')
    final_status = models.CharField(max_length=20, choices=FINAL_STATUS_CHOICES, default='Pending')

    accountant_remark = models.TextField(blank=True, null=True)
    manager_remark = models.TextField(blank=True, null=True)

    forwarded_to_manager = models.BooleanField(default=False)
    reviewed_by_manager = models.BooleanField(default=False)
    manager_reviewed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if hasattr(self, 'expense_type') and self.expense_type in ['travel-bike', 'travel-personal-car']:
            if not self.kilometers:
                raise ValidationError("Kilometers are required for bike/personal car travel.")
            self.amount = self.kilometers * (5 if self.expense_type == 'travel-bike' else 12)

        elif hasattr(self, 'expense_type') and self.expense_type == 'travel-cab':
            if not self.receipt:
                raise ValidationError("Receipt is mandatory for travel via cab.")
            if not self.amount:
                raise ValidationError("Amount is required for travel via cab.")

        else:
            if not self.amount:
                raise ValidationError("Amount is required for this expense type.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} | {self.amount} on {self.date}"

class SystemSettings(models.Model):
    expense_grace_days = models.PositiveIntegerField(
        default=10,
        help_text="Allowed days to submit backdated expenses."
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Expense grace: {self.expense_grace_days} days"

class EmployeeExpenseSetting(models.Model):
    employee = models.OneToOneField('employee.EmployeeProfile', on_delete=models.CASCADE)
    grace_period_days = models.PositiveIntegerField(default=10)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.grace_period_days} days"

class DailyAllowance(models.Model):
    timesheet = models.OneToOneField('timesheet.Timesheet', on_delete=models.CASCADE)
    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE)
    date = models.DateField()
    da_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    is_extended = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    forwarded_to_accountant = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class CountryDASetting(models.Model):
    country = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=10)
    da_rate_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hour_rate = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Country DA Rate Setting"
        verbose_name_plural = "Country DA Rate Settings"
        ordering = ['country']

    def __str__(self):
        return f"{self.country} ({self.currency}) - DA: {self.da_rate_per_hour}/hr, Extra: {self.extra_hour_rate}/hr"

class CountryDARate(models.Model):
    country = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=10)
    da_rate_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hour_rate = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.country} ({self.currency})"




class GlobalExpenseSettings(models.Model):
    days = models.PositiveIntegerField(default=5)

    def __str__(self):
        return f"{self.days} day(s)"

class EmployeeExpenseGrace(models.Model):
    employee = models.OneToOneField(EmployeeProfile, on_delete=models.CASCADE)
    days = models.PositiveIntegerField(default=5)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} – {self.days} day(s)"


# ✅ ADD THIS BELOW:
class GlobalDASettings(models.Model):
    local_da = models.DecimalField(max_digits=10, decimal_places=2, default=150)
    domestic_da = models.DecimalField(max_digits=10, decimal_places=2, default=350)
    international_da = models.DecimalField(max_digits=10, decimal_places=2, default=800)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"DA Rates: Local ₹{self.local_da}, Domestic ₹{self.domestic_da}, International ₹{self.international_da}"
