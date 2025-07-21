from django.urls import path
from accountant.views import (
    accountant_dashboard,
    expense_approval_dashboard,
    approve_or_reject_expense,
    approve_daily_allowance,
    export_expense_tab_excel,
    export_advance_expense_summary
)
from accountant.views.advance_views import (
    accountant_approve_advances,
    accountant_approve_advance
)

app_name = 'accountant'

urlpatterns = [
    path('expenses/', expense_approval_dashboard, name='expense-approval-dashboard'),
    path('expenses/<int:expense_id>/<str:action>/', approve_or_reject_expense, name='expense-action'),
    path('dashboard/', accountant_dashboard, name='dashboard'),
    path('approve-da/<int:da_id>/', approve_daily_allowance, name='approve-da'),
    path('export/<str:tab_name>/', export_expense_tab_excel, name='export-expense-tab'),
    
    # Advance Views - corrected names
    path('approve-advances/', accountant_approve_advances, name='accountant_approve_advances'),
    path('approve-advance/<int:advance_id>/', accountant_approve_advance, name='accountant_approve_advance'),
    
    path('export/advance-summary/', export_advance_expense_summary, name='export-advance-summary'),

]