from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import EmployeeProfile
from manager.models import EmployeeSkill, TaskAssignment
from .forms import EmployeeProfileForm
from project.models import Project

from employee.models import EmployeeProfile

from accounts.utils import get_dashboard_redirect_url
# employee/views.py





@login_required
def profile_home(request):
	profile, created = EmployeeProfile.objects.get_or_create(user=request.user)
	employee_skills = EmployeeSkill.objects.filter(employee=profile)

	if 'dashboard' in request.GET:
		redirect_url = get_dashboard_redirect_url(request.user)
		return redirect(redirect_url)

	context = {
		'profile': profile,
		'employee_skills': employee_skills,
		'debug_role': request.user.role
	}
	return render(request, 'employee/profile_home.html', context)


@login_required
def edit_profile(request):
    profile, created = EmployeeProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = EmployeeProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")

            user_role = request.user.role  # Always use CustomUser.role

            if user_role == 'Manager':
                return redirect('manager:manager-dashboard')
            elif user_role == 'HR':
                return redirect('hr:dashboard')
            elif user_role == 'Accountant':
                return redirect('accountant:dashboard')
            elif user_role == 'Director':
                return redirect('director:dashboard')
            else:
                return redirect('employee:employee-dashboard')
    else:
        form = EmployeeProfileForm(instance=profile)

    return render(request, 'employee/edit_profile.html', {'form': form})






@login_required
def employee_dashboard(request):
    profile = EmployeeProfile.objects.get(user=request.user)

    # Fetch recent assigned project IDs via TaskAssignment
    recent_project_ids = (
        TaskAssignment.objects
        .filter(employee=profile)
        .select_related('project')
        .order_by('-assigned_date')
        .values_list('project', flat=True)
        .distinct()[:3]
    )

    # Fetch actual project objects
    recent_projects = Project.objects.filter(id__in=recent_project_ids)

    return render(request, 'employee/employee_dashboard.html', {
        'profile': profile,  # ✅ Now passed to template
        'recent_projects': recent_projects,
    })




@login_required
def my_projects(request):
    profile = EmployeeProfile.objects.get(user=request.user)

    # Get project IDs assigned to this employee via TaskAssignment
    assigned_project_ids = (
        TaskAssignment.objects
        .filter(employee=profile)
        .values_list('project', flat=True)
        .distinct()
    )

    # Fetch actual Project instances using these IDs
    projects = Project.objects.filter(id__in=assigned_project_ids)

    return render(request, 'employee/my_projects.html', {
        'projects': projects,
    })
