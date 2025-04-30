from employee.models import EmployeeProfile
from django.urls import reverse

def get_effective_role(user):
    """Safe role retrieval that handles missing profiles"""
    try:
        profile = EmployeeProfile.objects.get(user=user)
        return profile.role
    except EmployeeProfile.DoesNotExist:
        if hasattr(user, 'is_staff') and user.is_staff:
            profile = EmployeeProfile.objects.create(user=user, role='Manager')
            return profile.role
        return 'Employee'

def get_dashboard_redirect_url(user):
    role = get_effective_role(user)

    role_redirects = {
        'Employee': 'employee:employee-dashboard',
        'Manager': 'manager:manager-dashboard',
        'HR': 'hr:dashboard',
        'Accountant': 'accountant:dashboard',
        'Director': 'director:dashboard',
        'Admin': '/admin/',  # Admin panel redirect as hardcoded fallback
    }

    destination = role_redirects.get(role, 'employee:employee-dashboard')

    # If it's a namespaced view, reverse it
    if isinstance(destination, str) and ':' in destination:
        return reverse(destination)

    return destination  # For hardcoded paths like '/admin/'
