from django.urls import path
from . import views

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
    path('expense-types/', views.manage_expense_types, name='manage-expense-types'),
]