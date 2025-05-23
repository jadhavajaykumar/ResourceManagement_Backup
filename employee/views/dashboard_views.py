# employee/views/dashboard_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from employee.models import EmployeeProfile, LeaveBalance
from employee.services.project_access import get_recent_assigned_projects
from project.models import Project

@login_required
def employee_dashboard(request):
    profile = EmployeeProfile.objects.get(user=request.user)
    leave_balance = LeaveBalance.objects.filter(employee=profile).first()

    recent_projects = get_recent_assigned_projects(profile)

    return render(request, 'employee/employee_dashboard.html', {
        'profile': profile,
        'leave_balance': leave_balance,
        'recent_projects': recent_projects,
    })
