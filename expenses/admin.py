from django.contrib import admin
from .models import Expense, ExpenseType
from .models import AdvanceRequest


@admin.register(ExpenseType)
class ExpenseTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'requires_kilometers', 'requires_receipt', 'rate_per_km')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    # Add your existing Expense admin configuration here
    list_display = ('date', 'project', 'new_expense_type', 'amount', 'status')
    # ... rest of your existing admin class fields/methods ...
    



@admin.register(AdvanceRequest)
class AdvanceRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'date_requested', 'approved_by_manager', 'approved_by_accountant', 'settled_by_account_manager']
    list_filter = ['approved_by_manager', 'approved_by_accountant', 'settled_by_account_manager']
    search_fields = ['employee__user__username', 'employee__user__first_name', 'employee__user__last_name']
    