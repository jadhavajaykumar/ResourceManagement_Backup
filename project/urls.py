from django.urls import path
from . import views
from . import views, assignment_views
from .views_reporting import (
    export_project_profitability_excel,
    export_project_profitability_pdf,
    export_da_claims_excel,
    export_timesheet_earnings_excel,
)


from project.views import get_tasks_by_project

app_name = 'project'

urlpatterns = [
    # Dashboard
    path('', views.project_dashboard, name='project-dashboard'),

    # Project CRUD
    path('edit-project/<int:project_id>/', views.edit_project, name='edit-project'),
    path('delete-project/<int:project_id>/', views.delete_project, name='delete-project'),

    # Task CRUD
    path('edit-task/<int:task_id>/', views.edit_task, name='edit-task'),
    path('delete-task/<int:task_id>/', views.delete_task, name='delete-task'),

    # AJAX
    path('ajax/get-country-rates/', views.get_country_rates, name='get-country-rates'),

    # Reports Export (Excel / PDF)
    path('report/profitability/<int:project_id>/excel/', export_project_profitability_excel, name='export_project_profitability_excel'),
    path('report/profitability/<int:project_id>/pdf/', export_project_profitability_pdf, name='export_project_profitability_pdf'),
    path('report/da-claims/<int:project_id>/excel/', export_da_claims_excel, name='export_da_claims_excel'),
    path('report/earnings/<int:project_id>/excel/', export_timesheet_earnings_excel, name='export_timesheet_earnings_excel'),
    
    path('api/get-tasks-by-project/', get_tasks_by_project, name='get_tasks_by_project'),
    
    # Task assignments
    path('assign-task/', assignment_views.assign_task, name='assign-task'),
    path('assign-task/load-tasks/', assignment_views.load_tasks, name='load-tasks'),
    path('assign-task/load-assignments/', assignment_views.load_assignments_ajax, name='load-assignments-ajax'),

    # Project dashboards
    path('summary/', assignment_views.project_summary_dashboard, name='project-summary-dashboard'),
    path('tracking/', assignment_views.project_tracking_dashboard, name='project-tracking-dashboard'),

]





