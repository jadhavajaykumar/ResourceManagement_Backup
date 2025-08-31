from .profile_views import profile_home, edit_profile
from .dashboard_views import employee_dashboard
from .employee_views import employee_list, employee_create
from .project_views import my_projects
from .attendance_views import attendance_report

__all__ = [
    "profile_home",
    "edit_profile",
    "employee_dashboard",
    "employee_list",
    "employee_create",
    "my_projects",
    "attendance_report",
]
