from employee.models import EmployeeProfile

def get_effective_role(user):
    """Safe role retrieval that handles missing profiles"""
    try:
        # Try to get existing profile
        profile = EmployeeProfile.objects.get(user=user)
        return profile.role
    except EmployeeProfile.DoesNotExist:
        # Create profile if missing (for staff users)
        if hasattr(user, 'is_staff') and user.is_staff:
            profile = EmployeeProfile.objects.create(user=user, role='Manager')
            return profile.role
        # Default fallback
        return 'Employee'

def get_dashboard_redirect_url(user):
    role = get_effective_role(user)
    role_redirects = {
        'Employee': 'employee:employee-dashboard',
        'Manager': 'manager:manager-dashboard',
        'HR': 'hr:dashboard',
        'Accountant': 'accountant:dashboard',
        'Director': 'director:dashboard',
        'Admin': '/admin/',
    }
    return role_redirects.get(role, 'employee:employee-dashboard')