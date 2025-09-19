from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
import logging
import json

from .models import Project, Task, Subtask
from .forms import ProjectForm, TaskForm, CountryRateForm, ProjectMaterialFormSet 
from .services.project_skill_service import save_required_skills
from .services.country_service import get_country_rate_details
try:
    from skills.models import MainSkill
except ImportError:  # Skills app may not be installed
    MainSkill = None
from expenses.models import CountryDARate

logger = logging.getLogger(__name__)

def has_project_access(user):
    return (
        user.has_perm("timesheet.can_approve")
        or user.groups.filter(name="Director").exists()
        or user.is_staff
    )

@login_required
@user_passes_test(has_project_access)
def project_dashboard(request):
    projects = Project.objects.prefetch_related('tasks', 'tasks__subtasks', 'required_skills').all()
    #main_skills = MainSkill.objects.all()
    main_skills = MainSkill.objects.all() if MainSkill else []
    if request.method == 'POST':
        if 'add_project' in request.POST:
            project_id = request.POST.get('project_id')
            instance = Project.objects.get(id=project_id) if project_id else None
            project_form = ProjectForm(request.POST, request.FILES, instance=instance)
            
            if project_form.is_valid():
                new_project = project_form.save()
               
                selected_skills = json.loads(request.POST.get('selected_skills') or '[]')

                if instance:
                    instance.required_skills.all().delete()

                save_required_skills(new_project, selected_skills)
                return redirect('project:project-dashboard')
            else:
                task_form = TaskForm()
                return render(request, 'project/project_dashboard.html', {
                    'projects': projects,
                    'project_form': project_form,
                    'task_form': task_form,
                    'main_skills': main_skills,
                })

        elif 'add_task' in request.POST:
            task_form = TaskForm(request.POST)
            if task_form.is_valid():
                task_form.save()
                return redirect('project:project-dashboard')
            else:
                project_form = ProjectForm()
                material_formset = ProjectMaterialFormSet(prefix='materials')
                return render(request, 'project/project_dashboard.html', {
                    'projects': projects,
                    'project_form': project_form,
                    'task_form': task_form,
                    'main_skills': main_skills,
                })

    project_form = ProjectForm()
    task_form = TaskForm()
    material_formset = ProjectMaterialFormSet(prefix='materials')
   

    return render(request, 'project/project_dashboard.html', {
        'projects': projects,
        'project_form': project_form,
        'task_form': task_form,
        'material_formset': material_formset,
        'main_skills': main_skills,
    })


@login_required
@user_passes_test(has_project_access)
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
@user_passes_test(has_project_access)
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    return redirect('project:project-dashboard')


@login_required
@user_passes_test(has_project_access)
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return redirect('project:project-dashboard')


def get_country_rates(request):
    country_id = request.GET.get('country_id')
    data = get_country_rate_details(country_id)
    if data:
        return JsonResponse(data)
    return JsonResponse({'error': 'Country not found'}, status=404)


@login_required
@user_passes_test(has_project_access)
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


@login_required
@user_passes_test(has_project_access)
def edit_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        material_formset = ProjectMaterialFormSet(request.POST, instance=project, prefix='materials')
        if form.is_valid() and material_formset.is_valid():
            form.save()
            material_formset.save()
            return redirect('project:project-dashboard')
    else:
        form = ProjectForm(instance=project)
        material_formset = ProjectMaterialFormSet(instance=project, prefix='materials')

    return render(request, 'project/edit_project.html', {
        'form': form,
        'material_formset': material_formset,
        'project': project
    })


def get_tasks_by_project(request):
    project_id = request.GET.get('project_id')
    tasks = Task.objects.filter(project_id=project_id).values('id', 'name')
    return JsonResponse({'tasks': list(tasks)})
