from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from employee.models import EmployeeProfile
from django.db.models import Sum
from django.db import models
from django.conf import settings
from project.models import Project


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
    max_amount_allowed = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Maximum reimbursable amount for this expense type")
    requires_travel_locations = models.BooleanField(default=False)
    requires_cooldown = models.BooleanField(default=False)
    cooldown_days = models.PositiveIntegerField(null=True, blank=True)
    

    def __str__(self):
        return self.name


class Expense(models.Model):
    STAGE_CHOICES = [
        ("ACCOUNTANT", "Accountant"),
        ("MANAGER", "Manager"),
        ("ACCOUNT_MANAGER", "Account Manager"),
        ("APPROVED", "Approved"),
        ("SETTLED", "Settled"),
        ("REJECTED", "Rejected"),
    ]
    
    STATUS_CHOICES = [
        ('Submitted', 'Submitted'),  # Employee submits
        ('Forwarded to Manager', 'Forwarded to Manager'),  # Accountant approved
        ('Forwarded to Account Manager', 'Forwarded to Account Manager'),  # Manager approved
        ('Approved', 'Approved'),  # Settled by Account Manager
        ('Settled', 'Settled'),
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
    current_stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default="ACCOUNTANT",
        blank=True
    )
    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE)
    date = models.DateField()
    kilometers = models.PositiveIntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    comments = models.TextField(blank=True)
    advance_used = models.ForeignKey('AdvanceRequest', null=True, blank=True, on_delete=models.SET_NULL, related_name='used_expenses')

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Submitted')
    reimbursed = models.BooleanField(default=False)

    accountant_remark = models.TextField(blank=True, null=True)
    manager_remark = models.TextField(blank=True, null=True)
    forwarded_to_manager = models.BooleanField(default=False)
    reviewed_by_manager = models.BooleanField(default=False)
    manager_reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    forwarded_to_accountmanager = models.BooleanField(default=False)

    from_location = models.CharField(max_length=100, null=True, blank=True)
    to_location = models.CharField(max_length=100, null=True, blank=True)

    def clean(self):
        if self.new_expense_type:
            if self.new_expense_type.name in ['Travel - Bike', 'Travel - Personal Car']:
                if not self.kilometers:
                    raise ValidationError("Kilometers are required for bike/personal car travel.")
            elif self.new_expense_type.name == 'Travel - Cab':
                if not self.receipt:
                    raise ValidationError("Receipt is mandatory for travel via cab.")
                if not self.amount:
                    raise ValidationError("Amount is required for travel via cab.")
            else:
                if not self.amount:
                    raise ValidationError("Amount is required for this expense type.")

    def save(self, *args, **kwargs):
        validate = kwargs.pop("validate", True)

        # ✅ Initialize current_stage only on creation
        if not self.pk and not self.current_stage:
            self.current_stage = "ACCOUNTANT"

        if validate:
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
    reimbursed = models.BooleanField(default=False)  # ✅ ADD THIS
    forwarded_to_accountant = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    forwarded_to_accountmanager = models.BooleanField(default=False)


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


class DailyAllowanceLog(models.Model):
    da_entry = models.ForeignKey('DailyAllowance', on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50)  # e.g., 'Created', 'Updated', 'Rejected'
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    remark = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.action} by {self.performed_by}"


class AdvanceRequest(models.Model): 
    STAGE_CHOICES = [
        ("MANAGER", "Manager"),
        ("ACCOUNTANT", "Accountant"),
        ("ACCOUNT_MANAGER", "Account Manager"),
        ("SETTLED", "Settled"),
        ("REJECTED", "Rejected"),
    ]

    STATUS_CHOICES = [
        ('Submitted', 'Submitted'),
        ('Forwarded to Manager', 'Forwarded to Manager'),
        ('Forwarded to Accountant', 'Forwarded to Accountant'),
        ('Forwarded to Account Manager', 'Forwarded to Account Manager'),
        ('Settled', 'Settled'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    adjusted_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Final amount after adjusting for previous negative balances"
    )
    purpose = models.TextField()
    date_requested = models.DateField(auto_now_add=True)

    approved_by_manager = models.BooleanField(default=False)
    approved_by_accountant = models.BooleanField(default=False)
    settled_by_account_manager = models.BooleanField(default=False)

    date_approved_by_accountant = models.DateTimeField(null=True, blank=True)
    settlement_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Submitted'
    )

    # ✅ New: current_stage tracking for unified flow
    current_stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default="MANAGER",
        blank=True
    )

    def save(self, *args, **kwargs):
        """Ensure current_stage is always initialized to MANAGER when first created."""
        if not self.pk:  # New advance request
            self.current_stage = "MANAGER"
        super().save(*args, **kwargs)

    def update_status(self):
        """Automatically update status based on approvals."""
        if self.settled_by_account_manager:
            self.status = 'Settled'
        elif self.approved_by_accountant:
            self.status = 'Forwarded to Account Manager'
        elif self.approved_by_manager:
            self.status = 'Forwarded to Accountant'
        else:
            self.status = 'Submitted'
        self.save(update_fields=['status'])

    def is_settled(self):
        return self.settled_by_account_manager

    @property
    def used_expenses(self):
        return Expense.objects.filter(advance_used=self)

    def current_balance(self):
        total_deducted = self.advanceadjustmentlog_set.aggregate(
            s=Sum("amount_deducted")
        )["s"] or 0
        return float(self.amount) - float(total_deducted)

    def can_raise_new(self):
        unsettled = AdvanceRequest.objects.filter(
            employee=self.employee,
            settled_by_account_manager=True
        ).order_by('-settlement_date')
        if not unsettled.exists():
            return True
        latest = unsettled.first()
        used_sum = latest.used_expenses.aggregate(Sum("amount"))["amount__sum"] or 0
        remaining_balance = latest.amount - used_sum
        return latest.settled_by_account_manager and remaining_balance <= 0
        
    @property
    def adjustments(self):
        return self.advanceadjustmentlog_set.select_related('expense')
    
    @property
    def total_used(self):
        return self.advanceadjustmentlog_set.aggregate(
            s=Sum("amount_deducted")
        )["s"] or 0

    @property
    def balance(self):
        return self.amount - self.total_used

    def __str__(self):
        return f"{self.employee.user.get_full_name()} | ₹{self.amount} | Requested: {self.date_requested}"


class AdvanceAdjustmentLog(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE)
    advance = models.ForeignKey(AdvanceRequest, on_delete=models.CASCADE)
    amount_deducted = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"₹{self.amount_deducted} from Advance {self.advance.id} for Expense {self.expense.id}"


