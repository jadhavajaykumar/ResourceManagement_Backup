from django.urls import path
from accountant.views import (
    accountant_dashboard,
    expense_approval_dashboard,
    approve_or_reject_expense
)

app_name = 'accountant'

urlpatterns = [
    path('expenses/', expense_approval_dashboard, name='expense-approval'),
    path('expenses/<int:expense_id>/<str:action>/', approve_or_reject_expense, name='expense-action'),
    path('dashboard/', accountant_dashboard, name='dashboard'),
]