from django.urls import path
from employee.views.attendance_views import attendance_c_off_report
from expenses.views.unified_expense_dashboard import unified_expense_dashboard
from .views import (
    profile_home, edit_profile,
    employee_dashboard,
    my_projects,
    attendance_report,
    advance_views
)
from employee.views.advance_views import raise_advance_request


app_name = 'employee'

urlpatterns = [
    path('profile/', profile_home, name='employee-profile-home'),
    path('edit-profile/', edit_profile, name='edit-profile'),
    path('dashboard/', employee_dashboard, name='employee-dashboard'),
    path('my-projects/', my_projects, name='my-projects'),
    path('attendance-report/', attendance_report, name='attendance-report'),
    path('attendance-c-off-report/', attendance_c_off_report, name='attendance-c-off-report'),
    path('raise-advance/', raise_advance_request, name='raise-advance-request'),
    #path('unified-expenses/', unified_expense_dashboard, name='unified-expense-dashboard'),
    #path('my-expenses/', unified_expense_dashboard, name='employee-expenses'),
    path('unified-expenses/', unified_expense_dashboard, name='unified-expense-dashboard'),

    

]



