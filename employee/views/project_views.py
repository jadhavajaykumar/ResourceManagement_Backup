# employee/views/project_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from employee.models import EmployeeProfile
from employee.services.project_access import get_assigned_projects_with_tasks
from project.models import Project, Task
from django.db.models import Prefetch
try:
    from skills.models import TaskAssignment
except ImportError:  # Skills app may not be installed
    TaskAssignment = None



@login_required
def my_projects(request):
    profile = EmployeeProfile.objects.get(user=request.user)

   # project_ids = TaskAssignment.objects.filter(employee=profile).values_list('project', flat=True)
    if TaskAssignment:
        task_ids = TaskAssignment.objects.filter(employee=profile).values_list('task', flat=True)
        tasks_qs = Task.objects.filter(id__in=task_ids).order_by('start_date')
    else:
        tasks_qs = Task.objects.none()
    projects = get_assigned_projects_with_tasks(profile)

    return render(request, 'employee/my_projects.html', {'projects': projects})
