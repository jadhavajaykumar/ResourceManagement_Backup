# expenses/admin.py
from django.contrib import admin
from .models import AdvanceRequest, AdvanceAdjustmentLog
from django.contrib import admin
from .models import Expense, ExpenseType



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
    list_display = (
        "id", "employee", "project", "amount",
        "status", "current_stage",
        "approved_by_manager", "approved_by_accountant", "settled_by_account_manager",
        "date_requested", "settlement_date",
    )
    list_filter = (
        "status", "current_stage",
        "approved_by_manager", "approved_by_accountant", "settled_by_account_manager",
        "project",
    )
    search_fields = (
        "purpose",
        "employee__user__first_name",
        "employee__user__last_name",
        "employee__user__email",
    )
    raw_id_fields = ("employee", "project")
    date_hierarchy = "date_requested"
    actions = ["hard_delete_selected"]

    def hard_delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()  # cascades will remove related AdvanceAdjustmentLog because of FK
        self.message_user(request, f"Deleted {count} advance request(s).")
    hard_delete_selected.short_description = "Delete selected advances"

@admin.register(AdvanceAdjustmentLog)
class AdvanceAdjustmentLogAdmin(admin.ModelAdmin):
    list_display = ("id", "advance", "expense", "amount_deducted", "created_at")
    search_fields = (
        "advance__employee__user__email",
        "advance__id",
        "expense__id",
    )
    raw_id_fields = ("advance", "expense")
    date_hierarchy = "created_at"
    