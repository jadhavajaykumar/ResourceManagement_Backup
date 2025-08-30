from employee.models import EmployeeProfile
from django.urls import reverse

def get_effective_role(user):
    """Safe role retrieval that handles missing profiles and normalizes roles"""
    try:
        profile = EmployeeProfile.objects.get(user=user)
        return normalize_role(profile.role)
    except EmployeeProfile.DoesNotExist:
        if user.has_perm('timesheet.can_approve'):
            profile = EmployeeProfile.objects.create(user=user, role='Manager')
            return 'Manager'
        return 'Employee'

def normalize_role(role):
    """Standardizes role strings (e.g., 'Account Manager' -> 'AccountManager')"""
    return role.strip().replace(" ", "")

def get_dashboard_redirect_url(user):

    """Return the unified dashboard home for all users."""
    return reverse("dashboard:home")
  

# Role check helpers (also normalized)
def is_manager(user):
    return get_effective_role(user) == 'Manager'

def is_hr(user):
    return get_effective_role(user) == 'HR'

def is_accountant(user):
    return get_effective_role(user) == 'Accountant'

def is_accountmanager(user):
    return get_effective_role(user) == 'AccountManager'
