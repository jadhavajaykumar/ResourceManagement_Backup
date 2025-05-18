from django.urls import path
from . import views
from .views import timesheet_approval_dashboard, handle_timesheet_action
app_name = 'manager'

urlpatterns = [
    path('dashboard/', views.manager_dashboard, name='manager-dashboard'),
    path('assign-skills/', views.assign_skills, name='assign-skills'),
    path('load-subskills/', views.load_subskills, name='load-subskills'),
    path('export-skill-matrix/', views.export_skill_matrix, name='export-skill-matrix'),
    path('get-employee-skill-data/', views.get_employee_skill_data, name='get-employee-skill-data'),
    path('edit-skill-assignment/', views.edit_skill_assignment, name='edit-skill-assignment'),
    path('assign-task/', views.assign_task, name='assign-task'),
    path('ajax/load-tasks/', views.load_tasks, name='ajax-load-tasks'),
    path('ajax/load-assignments/', views.load_assignments_ajax, name='load-assignments-ajax'),
    path('expenses/', views.expense_approval_dashboard, name='expense-approval'),
    path('expenses/<int:expense_id>/<str:action>/', views.handle_expense_action, name='expense-action'),
    path('timesheet-approvals/', timesheet_approval_dashboard, name='timesheet-approval'),
    path('timesheet-action/<int:timesheet_id>/<str:action>/', handle_timesheet_action, name='handle-timesheet-action'),
]

    
  

