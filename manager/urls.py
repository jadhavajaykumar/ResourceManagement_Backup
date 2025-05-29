# manager/urls.py

from django.urls import path
from manager.views.timesheet_views import approve_c_offs
from manager.views.c_off_views import c_off_approvals, approve_c_off, reject_c_off



from manager.views import (
    manager_dashboard,

    # Skill Management
    assign_skills,
    load_subskills,
    export_skill_matrix,
    get_employee_skill_data,
    edit_skill_assignment,

    # Task Assignment
    assign_task,
    load_tasks,
    load_assignments_ajax,

    # Expense Approval
    expense_approval_dashboard,
    expense_approvals,
    handle_expense_action,

    # Timesheet Approval
    timesheet_approval_dashboard,
    timesheet_approvals,
    handle_timesheet_action,
    filtered_timesheet_approvals,
    
    
   
    

    # Project Reports
    project_tracking_dashboard,
    project_summary_dashboard,
    project_detail,
)

app_name = 'manager'

urlpatterns = [
    # Dashboard
    path('', manager_dashboard, name='manager-dashboard'),

    # Skills
    path('assign-skills/', assign_skills, name='assign-skills'),
    path('load-subskills/', load_subskills, name='load-subskills'),
    path('export-skill-matrix/', export_skill_matrix, name='export-skill-matrix'),
    path('get-employee-skill-data/', get_employee_skill_data, name='get-employee-skill-data'),
    path('edit-skill-assignment/', edit_skill_assignment, name='edit-skill-assignment'),

    # Tasks
    path('assign-task/', assign_task, name='assign-task'),
    path('load-tasks/', load_tasks, name='load-tasks'),
    path('load-assignments-ajax/', load_assignments_ajax, name='load-assignments-ajax'),

    # Expenses
    path('expense-approval/', expense_approval_dashboard, name='expense-approval'),
    path('expense-approvals/', expense_approvals, name='expense-approvals'),
    path('handle-expense-action/<int:expense_id>/<str:action>/', handle_expense_action, name='handle-expense-action'),

    # Timesheets
    path('timesheet-approval/', timesheet_approval_dashboard, name='timesheet-approval'),
    path('timesheet-approvals/', timesheet_approvals, name='timesheet-approvals'),
    path('handle-timesheet-action/<int:timesheet_id>/<str:action>/', handle_timesheet_action, name='handle-timesheet-action'),
    path('filtered-timesheet-approvals/', filtered_timesheet_approvals, name='filtered-timesheet-approvals'),
    path('approve-c-offs/', approve_c_offs, name='approve-c-offs'),


    # Projects
    path('project-tracking/', project_tracking_dashboard, name='project-tracking'),
    path('project-summary/', project_summary_dashboard, name='project-summary'),
    path('project/<int:project_id>/', project_detail, name='project-detail'),
    
    # C-Off
    path('c-off-approvals/', c_off_approvals, name='c-off-approvals'),
    path('c-off-approvals/<int:application_id>/approve/', approve_c_off, name='approve-c-off'),
    path('c-off-approvals/<int:application_id>/reject/', reject_c_off, name='reject-c-off'),
]
