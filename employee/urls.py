# accounts/urls.py
from django.urls import path
from employee.views.attendance_views import attendance_c_off_report
from employee.views.employee_views import (
    export_employee_template,
    import_employees,
    export_user_template,
    import_users_accounts,
)

from expenses.views.unified_expense_dashboard import unified_expense_dashboard
from .views import (
    edit_profile,
    employee_dashboard,
    employee_list, employee_create,
    my_projects,
    attendance_report,
    
    
    
)
from employee.views.profile_views import profile_home







app_name = 'employee'

urlpatterns = [
    path('list/', employee_list, name='employee-list'),
    path('add/', employee_create, name='add-employee'),
    path('profile/', profile_home, name='employee-profile-home'),
    path('edit-profile/', edit_profile, name='edit-profile'),
    path('dashboard/', employee_dashboard, name='employee-dashboard'),
    path('my-projects/', my_projects, name='my-projects'),
    path('attendance-report/', attendance_report, name='attendance-report'),
    path('attendance-c-off-report/', attendance_c_off_report, name='attendance-c-off-report'),
    path('unified-expenses/', unified_expense_dashboard, name='unified-expense-dashboard'),
    
    path('export-template/', export_employee_template, name='export-template'),
    path('import/', import_employees, name='import-employees'),
    path('edit/<int:pk>/', employee_create, name='edit-employee'),
    
    
    # Bulk user account (admin) import/export
    path('user/export-template/', export_user_template, name='export-user-template'),
    path('user/import/', import_users_accounts, name='import-users'),


    

]



