from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.admin.views.decorators import staff_member_required

from .models import Project, Task, Subtask, ProjectRequiredSkill
from expenses.models import CountryDARate
from .forms import ProjectForm, TaskForm, SubtaskForm, CountryRateForm
import logging

logger = logging.getLogger(__name__)

def is_manager(user):
    if not user.is_authenticated:
        return False
    if user.role == 'Manager' or user.is_superuser:
        return True
    raise PermissionDenied

@login_required
@user_passes_test(is_manager)
def project_dashboard(request):
    projects = Project.objects.prefetch_related('tasks', 'tasks__subtasks', 'required_skills').all()

    if request.method == 'POST':
        if 'add_project' in request.POST:
            project_id = request.POST.get('project_id')
            instance = Project.objects.get(id=project_id) if project_id else None
            project_form = ProjectForm(request.POST, request.FILES, instance=instance)
            if project_form.is_valid():
                new_project = project_form.save()

                # ✅ Handle saving required skills
                import json
                #selected_skills_json = request.POST.get('selected_skills', '[]')
                #selected_skills = json.loads(selected_skills_json)
                
                selected_skills_json = request.POST.get('selected_skills') or '[]'
                selected_skills = json.loads(selected_skills_json)


                if instance:
                    # If editing, clear old required skills
                    instance.required_skills.all().delete()

                for skill in selected_skills:
                    main_skill_id = skill.get('main_skill_id')
                    subskill_id = skill.get('subskill_id')
                    if main_skill_id and subskill_id:
                        ProjectRequiredSkill.objects.create(
                            project=new_project,
                            main_skill_id=main_skill_id,
                            subskill_id=subskill_id
                        )

                return redirect('project:project-dashboard')
            else:
                return JsonResponse({'success': False, 'errors': project_form.errors})

        elif 'add_task' in request.POST:
            task_form = TaskForm(request.POST)
            if task_form.is_valid():
                task_form.save()
                return redirect('project:project-dashboard')
            else:
                return JsonResponse({'success': False, 'errors': task_form.errors})

    project_form = ProjectForm()
    task_form = TaskForm()

    # ⚡ Also pass available main_skills for dropdown rendering
    from manager.models import MainSkill
    main_skills = MainSkill.objects.all()

    return render(request, 'project/project_dashboard.html', {
        'projects': projects,
        'project_form': project_form,
        'task_form': task_form,
        'main_skills': main_skills,
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

def get_country_rates(request):
    country_id = request.GET.get('country_id')
    try:
        country = CountryDARate.objects.get(id=country_id)
        return JsonResponse({
            'da_rate_per_hour': str(country.da_rate_per_hour),
            'extra_hour_rate': str(country.extra_hour_rate),
            'currency': country.currency,
        })
    except CountryDARate.DoesNotExist:
        return JsonResponse({'error': 'Country not found'}, status=404)

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
    
@login_required
@user_passes_test(is_manager)
def edit_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            return redirect('project:project-dashboard')
    else:
        form = ProjectForm(instance=project)

    return render(request, 'project/edit_project.html', {
        'form': form,
        'project': project
    })
        