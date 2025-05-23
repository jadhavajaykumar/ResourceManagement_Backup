from django.urls import path

from .views.expense_entry import employee_expenses, edit_expense, delete_expense
from .views.expense_approval import approve_expense
from .views.expense_type_settings import edit_expense_type, delete_expense_type
from .views.grace_period import manage_expense_settings
from .views.country_da import manage_country_da, edit_country_da, delete_country_da
from .views.expense_type_settings import expense_settings_dashboard

app_name = 'expenses'

urlpatterns = [
    path('my-expenses/', employee_expenses, name='employee-expenses'),
    path('edit/<int:expense_id>/', edit_expense, name='edit-expense'),
    path('delete/<int:expense_id>/', delete_expense, name='delete-expense'),
    path('approve/<int:expense_id>/', approve_expense, name='approve-expense'),

    # Settings
    path('settings/', expense_settings_dashboard, name='expense-settings'),
    path('settings/edit-expense-type/<int:type_id>/', edit_expense_type, name='edit-expense-type'),
    path('settings/delete-expense-type/<int:type_id>/', delete_expense_type, name='delete-expense-type'),

    # Country DA
    path('manage-country-da/', manage_country_da, name='manage-country-da'),
    path('edit-country-da/<int:rate_id>/', edit_country_da, name='edit-country-da'),
    path('delete-country-da/<int:rate_id>/', delete_country_da, name='delete-country-da'),
]
