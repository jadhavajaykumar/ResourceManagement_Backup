from django.contrib import admin
from .models import Expense, ExpenseType

@admin.register(ExpenseType)
class ExpenseTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'requires_kilometers', 'requires_receipt', 'rate_per_km')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    # Add your existing Expense admin configuration here
    list_display = ('date', 'project', 'expense_type', 'amount', 'status')
    # ... rest of your existing admin class fields/methods ...