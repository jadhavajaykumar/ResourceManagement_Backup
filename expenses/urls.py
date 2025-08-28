# expenses/urls.py
from django.urls import path
from expenses.views.am_settlement import am_unsettled_summary, am_bulk_settle_employee

from .views.expense_entry import (
    employee_expenses, edit_expense, delete_expense,
    export_expense_tab, edit_expense_json, get_expense_data,
    new_expense_form, edit_advance_json, edit_advance, delete_advance,
)
from .views.expense_approval import approve_expense
from .views.expense_type_settings import (
    edit_expense_type, delete_expense_type,
    expense_settings_dashboard, get_expense_type_details,
)
from .views.grace_period import manage_expense_settings
from .views.country_da import manage_country_da, edit_country_da, delete_country_da
from .views.unified_expense_dashboard import unified_expense_dashboard
from .views.unified_actions import handle_expense_action
from .views.views_da_actions import (
    approve_weekend_da,
    reject_weekend_da,
    delete_weekend_da,
)
from .views.da_settlement import settle_da_view

# ✅ import the real callables for export
from expenses.views import reports

app_name = "expenses"

urlpatterns = [
    # Employee expense views
    path("my-expenses/", employee_expenses, name="employee-expenses"),

    # Edit/Delete Expense
    path("edit/<int:expense_id>/", edit_expense, name="edit-expense"),
    path("edit/<int:expense_id>/json/", edit_expense_json, name="edit-expense-json"),
    path("delete/<int:expense_id>/", delete_expense, name="delete-expense"),

    # Edit/Delete Advance
    path("advance/<int:advance_id>/edit/json/", edit_advance_json, name="edit-advance-json"),
    path("advance/<int:advance_id>/edit/", edit_advance, name="edit-advance"),
    path("advance/<int:advance_id>/delete/", delete_advance, name="delete-advance"),

    # New Expense (blank form for modal)
    path("new/form/", new_expense_form, name="new-expense-form"),

    # Approval
    path("approve/<int:expense_id>/", approve_expense, name="approve-expense"),

    # Export
    path("export-expense/<str:tab_name>/", export_expense_tab, name="export_expense_tab"),
    path("export/report/", reports.export_report, name="export-report"),
    path("export/report/csv/", reports.export_report_csv, name="export-report-csv"),

    # Settings
    path("settings/", expense_settings_dashboard, name="expense-settings"),
    path("settings/edit-expense-type/<int:expense_type_id>/", edit_expense_type, name="edit-expense-type"),
    path("settings/delete-expense-type/<int:expense_type_id>/", delete_expense_type, name="delete-expense-type"),
    path("get-expense-type-details/<int:type_id>/", get_expense_type_details, name="get-expense-type-details"),

    # Country DA
    path("manage-country-da/", manage_country_da, name="manage-country-da"),
    path("edit-country-da/<int:rate_id>/", edit_country_da, name="edit-country-da"),
    path("delete-country-da/<int:rate_id>/", delete_country_da, name="delete-country-da"),

    # Unified Dashboard
    path("unified-expense-dashboard/", unified_expense_dashboard, name="unified-expense-dashboard"),
    path(
        "unified/action/<str:item_type>/<int:item_id>/<str:action>/",
        handle_expense_action,
        name="unified-action",
    ),

    # Weekend DA actions
    path("da/weekend/<int:pk>/approve/", approve_weekend_da, name="da_weekend_approve"),
    path("da/weekend/<int:pk>/reject/",  reject_weekend_da,  name="da_weekend_reject"),
    path("da/weekend/<int:pk>/delete/",  delete_weekend_da,  name="da_weekend_delete"),

    # DA settlement (advance or cash/bank)
    path("da/settle/", settle_da_view, name="da_settle"),

    # Account Manager settlement summary + bulk settle
    path("am/settlements/", am_unsettled_summary, name="am-unsettled-summary"),
    path("am/settlements/<int:employee_id>/settle/", am_bulk_settle_employee, name="am-bulk-settle-employee"),
    path("am/settle/<int:employee_id>/", am_bulk_settle_employee, name="am_bulk_settle_employee"),

    # 🔁 Alias so the partial `{% url 'expenses:am_settle_employee' %}` resolves
    path("am/settle-employee/<int:employee_id>/", am_bulk_settle_employee, name="am_settle_employee"),
]
