# manager/views/task_views.py
from django.http import JsonResponse
from project.models import Task
from manager.models import TaskAssignment
from django.contrib.auth.decorators import login_required
from employee.models import EmployeeProfile

#@login_required
#def load_tasks(request):
#    project_id = request.GET.get('project')
 #   employee_id = request.GET.get('employee')
#
 #   if not project_id or not employee_id:
  #      return JsonResponse([], safe=False)
#
 ##      tasks = Task.objects.filter(
   #         project_id=project_id,
    #        id__in=TaskAssignment.objects.filter(
     #           employee_id=employee_id,
#                task__project_id=project_id
 #           ).values_list('task_id', flat=True)
 #       ).values('id', 'name')
#
 #       return JsonResponse(list(tasks), safe=False)
  #  except Exception as e:
   #     return JsonResponse({'error': str(e)}, status=500)
   
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

#@user_passes_test(is_manager)
@login_required
def load_tasks(request):
    project_id = request.GET.get('project')
    employee_id = request.GET.get('employee')

    logger.debug(f"[load_tasks] project={project_id}, employee={employee_id}")

    if not project_id:
        return JsonResponse([], safe=False)

    try:
        tasks = Task.objects.filter(project_id=project_id)
        logger.debug(f"[load_tasks] All project tasks: {[t.name for t in tasks]}")

        if employee_id:
            from employee.models import EmployeeProfile
            employee = EmployeeProfile.objects.get(id=employee_id)
            assigned_tasks = tasks.filter(taskassignment__employee=employee).distinct()
            logger.debug(f"[load_tasks] Assigned tasks: {[t.name for t in assigned_tasks]}")
            if assigned_tasks.exists():
                tasks = assigned_tasks

        return JsonResponse(list(tasks.values('id', 'name')), safe=False)

    except Exception as e:
        logger.error(f"[load_tasks] Error: {str(e)}", exc_info=True)
        return JsonResponse([], safe=False)

