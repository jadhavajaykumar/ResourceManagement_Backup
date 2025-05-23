# manager/views/timesheet_views.py
from django.shortcuts import render
from timesheet.models import Timesheet
from employee.models import EmployeeProfile
from project.models import Project
from django.contrib.auth.decorators import login_required, user_passes_test
from manager.views import is_manager

@login_required
@user_passes_test(is_manager)
def filtered_timesheet_dashboard(request):
    timesheets = Timesheet.objects.select_related('employee__user', 'project', 'task').all()
    projects = Project.objects.all()
    employees = EmployeeProfile.objects.all()

    # Apply filters
    if request.GET.get("start_date"):
        timesheets = timesheets.filter(date__gte=request.GET["start_date"])
    if request.GET.get("end_date"):
        timesheets = timesheets.filter(date__lte=request.GET["end_date"])
    if request.GET.get("project"):
        timesheets = timesheets.filter(project_id=request.GET["project"])
    if request.GET.get("employee"):
        timesheets = timesheets.filter(employee_id=request.GET["employee"])
    if request.GET.get("status"):
        timesheets = timesheets.filter(status=request.GET["status"])

    context = {
        "timesheets": timesheets,
        "projects": projects,
        "employees": employees,
        "current_page": "timesheets"
    }
    return render(request, "manager/timesheet_filtered_dashboard.html", context)
