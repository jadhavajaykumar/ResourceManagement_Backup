from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.db.models import Sum
from datetime import datetime

from skills.models import TaskAssignment
from employee.models import EmployeeProfile
from .models import Project, Task
from .forms import TaskAssignmentForm
from .services.progress_service import calculate_project_progress
from timesheet.models import Timesheet
from expenses.models import Expense


@login_required
@permission_required('timesheet.can_approve')
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
                return redirect('project:assign-task')
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Invalid assignment ID'})
                return redirect('project:assign-task')

        # Edit task assignment
        elif 'edit_task' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(TaskAssignment, id=assignment_id)
            form = TaskAssignmentForm(request.POST, instance=assignment)
            if form.is_valid():
                form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('project:assign-task')

        # New task assignment
        else:
            form = TaskAssignmentForm(request.POST)
            if form.is_valid():
                form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('project:assign-task')
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


@login_required
@permission_required('timesheet.can_approve')
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

@login_required
@permission_required('timesheet.can_approve')
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
    
@login_required
@permission_required('timesheet.can_approve')
def project_summary_dashboard(request):
    projects = Project.objects.all()
    project_data = []

    for project in projects:
        timesheets = Timesheet.objects.filter(project=project, status='Approved')
        expenses_qs = Expense.objects.filter(project=project, status='Approved')
        total_hours = sum(
            (datetime.combine(t.date, t.time_to) - datetime.combine(t.date, t.time_from)).total_seconds() / 3600
            for t in timesheets
        )
        total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or 0
        project_data.append({
            'project': project,
            'total_hours': total_hours,
            'total_expenses': total_expenses,
        })

    return render(request, 'project/project_summary_dashboard.html', {'projects': project_data})


@login_required
@permission_required('timesheet.can_approve')
def project_tracking_dashboard(request):
    projects = Project.objects.all()
    project_data = []

    for project in projects:
        data = calculate_project_progress(project)
        project_data.append({
            'project': project,
            'expenses': data['total_expense'],
            'earnings': data['earnings'],
            'days_worked': data['days_worked'],
            'budget_utilized': data['budget_utilized'],
        })

    return render(request, 'project/project_tracking_dashboard.html', {'projects': project_data})    