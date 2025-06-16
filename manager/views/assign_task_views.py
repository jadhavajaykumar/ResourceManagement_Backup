from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from ..models import TaskAssignment
from employee.models import EmployeeProfile
from project.models import Task
from ..forms import TaskAssignmentForm
from django.db import transaction
from accounts.access_control import is_manager_or_admin, is_manager


@login_required
@user_passes_test(is_manager)
def assign_task(request):
    assignments = TaskAssignment.objects.select_related('employee__user', 'project', 'task').order_by('-assigned_date')

    if request.method == "POST":
        # Unassign task
        if 'unassign_task' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            if assignment_id and assignment_id.isdigit():
                TaskAssignment.objects.filter(id=assignment_id).delete()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('manager:assign-task')
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Invalid assignment ID'})
                return redirect('manager:assign-task')

        # Edit task assignment
        elif 'edit_task' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(TaskAssignment, id=assignment_id)
            form = TaskAssignmentForm(request.POST, instance=assignment)
            if form.is_valid():
                form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('manager:assign-task')
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': form.errors})
                # Re-render page if normal POST fails validation
                return render(request, 'manager/assign_task.html', {
                    'form': form,
                    'assignments': assignments,
                })

        # New task assignment
        else:
            form = TaskAssignmentForm(request.POST)
            if form.is_valid():
                form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('manager:assign-task')
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TaskAssignmentForm()

    return render(request, 'manager/assign_task.html', {
        'form': form,
        'assignments': assignments,
    })


from django.contrib.auth.decorators import login_required

@user_passes_test(is_manager)
@login_required
def load_tasks(request):
    project_id = request.GET.get('project')
    employee_id = request.GET.get('employee')
    
    if not project_id:
        return JsonResponse([], safe=False)
    
    # Get base tasks
    tasks = Task.objects.filter(project_id=project_id)
    
    # Filter by employee assignment if employee ID is provided
    if employee_id:
        try:
            employee = EmployeeProfile.objects.get(id=employee_id)
            assigned_tasks = tasks.filter(taskassignment__employee=employee).distinct()
            if assigned_tasks.exists():
                tasks = assigned_tasks
        except EmployeeProfile.DoesNotExist:
            pass
    
    return JsonResponse(list(tasks.values('id', 'name')), safe=False)

@user_passes_test(is_manager)
@login_required
def load_assignments_ajax(request):
    assignments = TaskAssignment.objects.select_related('employee__user', 'project', 'task').order_by('-assigned_date')
    data = [
        {
            'id': a.id,
            'employee': a.employee.user.get_full_name(),
            'project': a.project.name if a.project else "-",
            'task': a.task.name if a.task else "-",
            'date': a.assigned_date.strftime('%Y-%m-%d'),
        }
        for a in assignments
    ]
    return JsonResponse({'assignments': data})