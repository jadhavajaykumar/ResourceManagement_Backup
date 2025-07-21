from django.urls import path
from accountmanager.views import advance_views
from accountmanager.views.dashboard_views import (
    dashboard_view,
    reimbursement_dashboard,
    settlement_summary,
    settle_employee,
    export_settlement_summary_excel,
    settle_selected,
    export_tab1,
    export_tab2,
    export_tab3,
    
)



app_name = 'accountmanager'

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('reimbursements/', reimbursement_dashboard, name='reimbursement_dashboard'),
    path('settlement-summary/', settlement_summary, name='settlement-summary'),
    path('settle/<int:employee_id>/', settle_employee, name='settle-employee'),
    path('export-summary/', export_settlement_summary_excel, name='export-settlement-summary'),
    path('settle-selected/', settle_selected, name='settle-selected'),
    
    path("export/tab1/", export_tab1, name="export_tab1"),
    path("export/tab2/", export_tab2, name="export_tab2"),
    path("export/tab3/", export_tab3, name="export_tab3"),
    
    path('settle-advances/', advance_views.settle_advances, name='settle-advances'),
    path('settle-advance/<int:advance_id>/', advance_views.settle_advance, name='settle-advance'),
    

]
