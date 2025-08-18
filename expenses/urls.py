from django.urls import path

from .views.expense_entry import (
    employee_expenses, edit_expense, delete_expense,
    export_expense_tab, edit_expense_json, get_expense_data,
    new_expense_form, edit_advance_json, edit_advance, delete_advance
)
from .views.expense_approval import approve_expense
from .views.expense_type_settings import (
    edit_expense_type, delete_expense_type,
    expense_settings_dashboard, get_expense_type_details
)
from .views.grace_period import manage_expense_settings
from .views.country_da import manage_country_da, edit_country_da, delete_country_da
from expenses.views.unified_expense_dashboard import unified_expense_dashboard
from expenses.views.unified_actions import handle_expense_action

app_name = 'expenses'

urlpatterns = [
    # Employee expense views
    path('my-expenses/', employee_expenses, name='employee-expenses'),

    # Edit/Delete Expense
    path('edit/<int:expense_id>/', edit_expense, name='edit-expense'),
    path('edit/<int:expense_id>/json/', get_expense_data, name='edit-expense-json'),
    path('delete/<int:expense_id>/', delete_expense, name='delete-expense'),
    
    # Edit/Delete Advance
    

    path('advance/<int:advance_id>/edit/json/', edit_advance_json, name='edit-advance-json'),
    path('advance/<int:advance_id>/edit/', edit_advance, name='edit-advance'),
    path('advance/<int:advance_id>/delete/', delete_advance, name='delete-advance'),




    # New Expense (blank form for modal)
    path('new/form/', new_expense_form, name='new-expense-form'),

    # Approval
    path('approve/<int:expense_id>/', approve_expense, name='approve-expense'),

    # Export
    path('export-expense/<str:tab_name>/', export_expense_tab, name='export_expense_tab'),

    # Settings
    path('settings/', expense_settings_dashboard, name='expense-settings'),
    path('settings/edit-expense-type/<int:expense_type_id>/', edit_expense_type, name='edit-expense-type'),
    path('settings/delete-expense-type/<int:expense_type_id>/', delete_expense_type, name='delete-expense-type'),
    path('get-expense-type-details/<int:type_id>/', get_expense_type_details, name='get-expense-type-details'),

    # Country DA
    path('manage-country-da/', manage_country_da, name='manage-country-da'),
    path('edit-country-da/<int:rate_id>/', edit_country_da, name='edit-country-da'),
    path('delete-country-da/<int:rate_id>/', delete_country_da, name='delete-country-da'),

    # Unified Dashboard
    path('unified-expense-dashboard/', unified_expense_dashboard, name='unified-expense-dashboard'),
    path('unified/action/<str:item_type>/<int:item_id>/<str:action>/', handle_expense_action, name='unified-action'),
    
    
]
