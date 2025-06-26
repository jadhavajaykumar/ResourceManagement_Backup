

from django.urls import path
from accountmanager.views.dashboard_views import (
    dashboard_view,
    reimbursement_dashboard,
    settlement_summary,
    settle_employee,
    export_settlement_summary_excel,
    settle_selected,
)



app_name = 'accountmanager'

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('reimbursements/', reimbursement_dashboard, name='reimbursement_dashboard'),
    path('settlement-summary/', settlement_summary, name='settlement-summary'),
    path('settle/<int:employee_id>/', settle_employee, name='settle-employee'),
    path('export-summary/', export_settlement_summary_excel, name='export-settlement-summary'),
    path('settle-selected/', settle_selected, name='settle-selected'),
]
