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

# New imports
from django import forms
from accounts.models import CustomUser

def _is_hr_or_admin(user):
    """Reuse logic used elsewhere: superuser OR HR group OR timesheet.can_approve permission."""
    return user.is_superuser or user.groups.filter(name='HR').exists() or user.has_perm('timesheet.can_approve')

# Restricted form for employees editing their own profile (only personal fields)
class EmployeeSelfEditForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = [
            'date_of_birth',
            'contact_number',
            'address',
            'emergency_contact_name',
            'emergency_contact_relation',
            'emergency_contact_number',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

# Small form for editing only user name fields
class UserNameForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


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
    """
    Edit profile:
     - HR/admin: full EmployeeProfileForm (unchanged behavior)
     - Regular employee: view all fields, but only personal fields + name are editable.
    """
    profile, _ = EmployeeProfile.objects.get_or_create(user=request.user)

    is_hr_admin = _is_hr_or_admin(request.user)

    redirect_map = {
        'Manager': 'timesheet:timesheet-approval',
        'HR': 'hr:dashboard',
        'Accountant': 'expenses:expense-approval-dashboard',
        'Director': 'director:dashboard',
    }

    if request.method == 'POST':
        if is_hr_admin:
            # full edit
            form = EmployeeProfileForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated successfully.")
                role = request.user.role
                return redirect(redirect_map.get(role, 'employee:employee-dashboard'))
            else:
                messages.error(request, "Please correct the errors below.")
                user_form = None
                profile_form = None
        else:
            # employee: only personal fields + name can change
            user_form = UserNameForm(request.POST, instance=request.user)
            profile_form = EmployeeSelfEditForm(request.POST, instance=profile)

            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, "Your personal details have been updated.")
                role = request.user.role
                return redirect(redirect_map.get(role, 'employee:employee-dashboard'))
            else:
                messages.error(request, "Please correct the errors below.")
                form = None
    else:
        # GET
        if is_hr_admin:
            form = EmployeeProfileForm(instance=profile)
            user_form = None
            profile_form = None
        else:
            form = None
            user_form = UserNameForm(instance=request.user)
            profile_form = EmployeeSelfEditForm(instance=profile)

    # Build a read-only display dict so that employees can *see* all fields even if they cannot edit them.
    def _fmt_date(d):
        return d.isoformat() if d else None

    display = {
        # USER
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,

        # EMPLOYMENT
        'employee_id': profile.employee_id,
        'role': profile.role,
        'department': profile.department,
        'reporting_manager': profile.reporting_manager.get_full_name() if profile.reporting_manager else None,
        'reporting_manager_email': profile.reporting_manager.email if profile.reporting_manager else None,
        'employment_type': profile.employment_type,
        'career_start_date': _fmt_date(profile.career_start_date),
        'probotix_joining_date': _fmt_date(profile.probotix_joining_date),
        'confirmation_date': _fmt_date(profile.confirmation_date),

        # PERSONAL
        'date_of_birth': _fmt_date(profile.date_of_birth),
        'contact_number': profile.contact_number,
        'address': profile.address,

        # EMERGENCY
        'emergency_contact_name': profile.emergency_contact_name,
        'emergency_contact_relation': profile.emergency_contact_relation,
        'emergency_contact_number': profile.emergency_contact_number,

        # BANK / LEGAL
        'pan_aadhar_ssn': profile.pan_aadhar_ssn,
        'bank_account_number': profile.bank_account_number,
        'bank_ifsc_code': profile.bank_ifsc_code,
        'epf_number': profile.epf_number,
        'grace_period_days': profile.grace_period_days,
    }

    return render(request, 'employee/edit_profile.html', {
        'form': form,                     # full form for HR
        'user_form': user_form,           # partial form for employee (name)
        'profile_form': profile_form,     # partial form for employee (personal fields)
        'is_hr_admin': is_hr_admin,
        'display': display,               # read-only values to show to non-HR users
    })
