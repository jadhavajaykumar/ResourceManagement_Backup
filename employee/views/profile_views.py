# employee/views/profile_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from employee.models import EmployeeProfile
try:
    from manager.services.skills import get_employee_skills
except ImportError:  # Manager app removed
    def get_employee_skills(profile):
        return []
from employee.forms import EmployeeProfileForm
from accounts.utils import get_dashboard_redirect_url

@login_required
def profile_home(request):
    profile, _ = EmployeeProfile.objects.get_or_create(user=request.user)
    employee_skills = get_employee_skills(profile)

    if 'dashboard' in request.GET:
        return redirect(get_dashboard_redirect_url(request.user))

    return render(request, 'employee/profile_home.html', {
        'profile': profile,
        'employee_skills': employee_skills,
        'debug_role': request.user.role,
    })


@login_required
def edit_profile(request):
    profile, _ = EmployeeProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = EmployeeProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            role = request.user.role
            redirect_map = {
                'Manager': 'timesheet:timesheet-approval',
                'HR': 'hr:dashboard',
                'Accountant': 'expenses:expense-approval-dashboard',
                'Director': 'director:dashboard',
            }
            return redirect(redirect_map.get(role, 'employee:employee-dashboard'))
    else:
        form = EmployeeProfileForm(instance=profile)

    return render(request, 'employee/edit_profile.html', {'form': form})
