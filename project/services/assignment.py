# project/services/assignment.py

try:
    from manager.models import TaskAssignment
except ImportError:  # Manager app removed
    TaskAssignment = None
from project.models import Project

def get_assigned_projects(employee):
    """Return a queryset of projects assigned to a given employee."""
    if not TaskAssignment:
        return Project.objects.none()
    project_ids = TaskAssignment.objects.filter(
        employee=employee
    ).values_list('project_id', flat=True).distinct()
    
    return Project.objects.filter(id__in=project_ids)
