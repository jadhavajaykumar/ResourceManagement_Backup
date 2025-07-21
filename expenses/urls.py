from django.urls import path

from .views.expense_entry import employee_expenses, edit_expense, delete_expense, export_expense_tab
from .views.expense_approval import approve_expense
from .views.expense_type_settings import edit_expense_type, delete_expense_type
from .views.grace_period import manage_expense_settings
from .views.country_da import manage_country_da, edit_country_da, delete_country_da
from .views.expense_type_settings import expense_settings_dashboard
from .views.expense_type_settings import get_expense_type_details

app_name = 'expenses'

urlpatterns = [
    path('my-expenses/', employee_expenses, name='employee-expenses'),
    path('edit/<int:expense_id>/', edit_expense, name='edit-expense'),
    path('delete/<int:expense_id>/', delete_expense, name='delete-expense'),
    path('approve/<int:expense_id>/', approve_expense, name='approve-expense'),
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
]
