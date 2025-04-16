# project/views.py



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Project, Task, Subtask, CountryDARate
from .forms import ProjectForm, TaskForm, SubtaskForm, CountryRateForm
import logging


from django.contrib.admin.views.decorators import staff_member_required






logger = logging.getLogger(__name__)

#def is_manager(user):
    #return user.is_authenticated and (user.is_superuser or user.role == 'Manager')
from django.core.exceptions import PermissionDenied

def is_manager(user):
    if not user.is_authenticated:
        return False
    if user.role == 'Manager' or user.is_superuser:
        return True
    raise PermissionDenied
    


@login_required
@user_passes_test(is_manager)
def project_dashboard(request):
    projects = Project.objects.prefetch_related('tasks', 'tasks__subtasks').all()

    if request.method == 'POST':
        if 'add_project' in request.POST:
            project_form = ProjectForm(request.POST, request.FILES)
            task_form = TaskForm()
            if project_form.is_valid():
                project_form.save()
                return redirect('project:project-dashboard')
        elif 'add_task' in request.POST:
            task_form = TaskForm(request.POST)
            project_form = ProjectForm()
            if task_form.is_valid():
                task_form.save()
                return redirect('project:project-dashboard')
    else:
        project_form = ProjectForm()
        task_form = TaskForm()

    return render(request, 'project/project_dashboard.html', {
        'projects': projects,
        'project_form': project_form,
        'task_form': task_form,
    })

@login_required
@user_passes_test(is_manager)
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('project:project-dashboard')
    else:
        form = TaskForm(instance=task)
    return render(request, 'project/edit_task.html', {'form': form, 'task': task})


@login_required
@user_passes_test(is_manager)
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    return redirect('project:project-dashboard')


@login_required
@user_passes_test(is_manager)
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return redirect('project:project-dashboard')



@login_required
@staff_member_required
def manage_country_rates(request):
    if request.method == 'POST':
        form = CountryRateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('project:manage-country-rates')
    else:
        form = CountryRateForm()

    rates = CountryDARate.objects.all()
    return render(request, 'project/manage_country_rates.html', {'form': form, 'rates': rates})

from django.http import JsonResponse
from .models import CountryDARate

def get_country_rates(request):
    country_id = request.GET.get('country_id')
    try:
        country = CountryDARate.objects.get(id=country_id)
        return JsonResponse({
            'da_rate_per_hour': str(country.da_rate_per_hour),
            'extra_hour_rate': str(country.extra_hour_rate),
            'currency_code': country.currency_code,
        })
    except CountryDARate.DoesNotExist:
        return JsonResponse({'error': 'Country not found'}, status=404)




#def is_manager(user):
  # return user.groups.filter(name="Manager").exists()

@login_required
@user_passes_test(is_manager)
def manage_country_rates(request):
    rates = CountryDARate.objects.all()
    form = CountryRateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('project:manage-country-rates')

    return render(request, 'project/manage_country_rates.html', {
        'form': form,
        'rates': rates,
    })
