from employee.models import EmployeeProfile
from django.urls import reverse

def get_effective_role(user):
    """Safe role retrieval that handles missing profiles and normalizes roles"""
    try:
        profile = EmployeeProfile.objects.get(user=user)
        return normalize_role(profile.role)
    except EmployeeProfile.DoesNotExist:
        if hasattr(user, 'is_staff') and user.is_staff:
            profile = EmployeeProfile.objects.create(user=user, role='Manager')
            return 'Manager'
        return 'Employee'

def normalize_role(role):
    """Standardizes role strings (e.g., 'Account Manager' -> 'AccountManager')"""
    return role.strip().replace(" ", "")

def get_dashboard_redirect_url(user):
    role = get_effective_role(user)

    role_redirects = {
        'Employee': 'employee:employee-dashboard',
        'Manager': 'manager:manager-dashboard',
        'HR': 'hr:dashboard',
        'Accountant': 'accountant:dashboard',
        'Director': 'director:dashboard',
        'Admin': '/admin/',
        'AccountManager': 'accountmanager:dashboard',  # key normalized
    }

    destination = role_redirects.get(role, 'employee:employee-dashboard')

    # If it's a namespaced view, reverse it
    if isinstance(destination, str) and ':' in destination:
        return reverse(destination)

    return destination  # For hardcoded paths like '/admin/'

# Role check helpers (also normalized)
def is_manager(user):
    return get_effective_role(user) == 'Manager'

def is_hr(user):
    return get_effective_role(user) == 'HR'

def is_accountant(user):
    return get_effective_role(user) == 'Accountant'

def is_accountmanager(user):
    return get_effective_role(user) == 'AccountManager'
