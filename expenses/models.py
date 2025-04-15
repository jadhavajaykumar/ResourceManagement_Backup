from django.db import models
from django.core.exceptions import ValidationError
from employee.models import EmployeeProfile


from django.core.exceptions import ValidationError

from project.models import Project

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()





class ExpenseType(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Correct reference
        on_delete=models.SET_NULL,
        null=True
        )
    name = models.CharField(max_length=50, unique=True)
    requires_kilometers = models.BooleanField(default=False)
    requires_receipt = models.BooleanField(default=False)
    rate_per_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    #created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    # Temporary fields for migration
    EXPENSE_TYPE_CHOICES = [
        ('travel-bike', 'Travel - Bike'),
        ('travel-personal-car', 'Travel - Personal Car'),
        ('travel-public', 'Travel - Public Transport'),
        ('travel-cab', 'Travel - Cab'),
        ('other', 'Other'),
    ]
    
   # Temporary fields
    expense_type = models.CharField(max_length=50)  # Old field
    new_expense_type = models.ForeignKey(
        'ExpenseType',
        on_delete=models.PROTECT,
        null=True,
        blank=True
        )
    # Keep other existing fields
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    date = models.DateField()
    kilometers = models.PositiveIntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    comments = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

  

    def clean(self):
        # Validate fields before saving
        if self.expense_type in ['travel-bike', 'travel-personal-car']:
            if not self.kilometers:
                raise ValidationError("Kilometers are required for bike/personal car travel.")
            self.amount = self.kilometers * (5 if self.expense_type == 'travel-bike' else 12)

        elif self.expense_type == 'travel-cab':
            if not self.receipt:
                raise ValidationError("Receipt is mandatory for travel via cab.")
            if not self.amount:
                raise ValidationError("Amount is required for travel via cab.")

        else:  # Public transport or other
            if not self.amount:
                raise ValidationError("Amount is required for this expense type.")
        pass

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    

    def __str__(self):
        return f"{self.employee.user.get_full_name()} | {self.get_expense_type_display()} | {self.amount} on {self.date}"

