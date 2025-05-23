from django.urls import path
from .views import (
    profile_home, edit_profile,
    employee_dashboard,
    my_projects,
    attendance_report
)

app_name = 'employee'

urlpatterns = [
    path('profile/', profile_home, name='employee-profile-home'),
    path('edit-profile/', edit_profile, name='edit-profile'),
    path('dashboard/', employee_dashboard, name='employee-dashboard'),
    path('my-projects/', my_projects, name='my-projects'),
    path('attendance-report/', attendance_report, name='attendance-report'),
]
