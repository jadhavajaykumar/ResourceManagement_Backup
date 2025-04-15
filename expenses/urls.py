from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('my-expenses/', views.employee_expenses, name='employee-expenses'),
    path('edit/<int:expense_id>/', views.edit_expense, name='edit-expense'),  # NEW
    path('delete/<int:expense_id>/', views.delete_expense, name='delete-expense'),  # New
    path('approve/<int:expense_id>/', views.approve_expense, name='approve-expense'),
    
    
]