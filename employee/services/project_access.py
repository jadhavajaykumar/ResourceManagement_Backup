# employee/services/project_access.py

try:
      from skills.models import TaskAssignment
except ImportError:  # Skills app may not be installed
    TaskAssignment = None
from project.models import Project, Task
from django.db.models import Prefetch

def get_assigned_project_ids(employee):
    if not TaskAssignment:
        return []
    return TaskAssignment.objects.filter(employee=employee).values_list('project', flat=True).distinct()

def get_assigned_task_ids(employee):
    if not TaskAssignment:
        return []
    return TaskAssignment.objects.filter(employee=employee).values_list('task', flat=True).distinct()

def get_assigned_projects_with_tasks(employee):
    project_ids = get_assigned_project_ids(employee)
    task_ids = get_assigned_task_ids(employee)
    tasks_qs = Task.objects.filter(id__in=task_ids).order_by('start_date')
    return Project.objects.filter(id__in=project_ids).prefetch_related(Prefetch('tasks', queryset=tasks_qs))

def get_recent_assigned_projects(employee, limit=3):
    if not TaskAssignment:
        return Project.objects.none()
    recent_project_ids = (
        TaskAssignment.objects
        .filter(employee=employee)
        .values_list('project', flat=True)
        .distinct()[:limit]
    )
    return Project.objects.filter(id__in=recent_project_ids)
