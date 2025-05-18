from django.urls import path
from . import views
from .views_reporting import (
    export_project_profitability_excel,
    export_project_profitability_pdf,
    export_da_claims_excel,
    export_timesheet_earnings_excel,
    )

app_name = 'project'

urlpatterns = [
    path('', views.project_dashboard, name='project-dashboard'),
    path('edit-task/<int:task_id>/', views.edit_task, name='edit-task'),
    path('delete-project/<int:project_id>/', views.delete_project, name='delete-project'),
    path('delete-task/<int:task_id>/', views.delete_task, name='delete-task'),
    path('ajax/get-country-rates/', views.get_country_rates, name='get-country-rates'),
    path('edit-project/<int:project_id>/', views.edit_project, name='edit-project'),
     path('report/profitability/<int:project_id>/excel/', export_project_profitability_excel, name='export_project_profitability_excel'),
    path('report/profitability/<int:project_id>/pdf/', export_project_profitability_pdf, name='export_project_profitability_pdf'),
    path('report/da-claims/<int:project_id>/excel/', export_da_claims_excel, name='export_da_claims_excel'),
    path('report/earnings/<int:project_id>/excel/', export_timesheet_earnings_excel, name='export_timesheet_earnings_excel'),


]



