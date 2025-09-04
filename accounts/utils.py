from employee.models import EmployeeProfile
from django.urls import reverse
from django.urls import reverse, NoReverseMatch

def _try(names):
    from django.urls import reverse, NoReverseMatch
    for n in names:
        try:
            return reverse(n)
        except NoReverseMatch:
            continue
    return reverse("dashboard:home")  # fallback (must exist)

def get_dashboard_redirect_url(user):
    # Unified landing for all roles
    return _try([
        "dashboard:home",
        #"accounts:profile",
        "employee:unified-expense-dashboard",
    ])        

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

  

# Role check helpers (also normalized)
def is_manager(user):
    return get_effective_role(user) == 'Manager'

def is_hr(user):
    return get_effective_role(user) == 'HR'

def is_accountant(user):
    return get_effective_role(user) == 'Accountant'

def is_accountmanager(user):
    return get_effective_role(user) == 'AccountManager'
    
        
        

