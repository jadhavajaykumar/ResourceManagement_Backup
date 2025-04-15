# project/views.py



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Project, Task, Subtask
from .forms import ProjectForm, TaskForm, SubtaskForm
import logging






logger = logging.getLogger(__name__)

def is_manager(user):
    return user.is_authenticated and user.role == 'Manager'

@login_required
@user_passes_test(is_manager)
def project_dashboard(request):
    projects = Project.objects.prefetch_related('tasks', 'tasks__subtasks').all()
    project_form = ProjectForm()
    task_form = TaskForm()

    if request.method == 'POST':
        if 'add_project' in request.POST:
            project_form = ProjectForm(request.POST, request.FILES)
            if project_form.is_valid():
                project_form.save()
                return redirect('project:project-dashboard')

        elif 'add_task' in request.POST:
            task_form = TaskForm(request.POST)
            if task_form.is_valid():
                task_form.save()
                return redirect('project:project-dashboard')

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

