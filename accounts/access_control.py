# account/access_control.py
import logging
logger = logging.getLogger(__name__)


def is_manager_or_admin(user):
    return user.is_authenticated and (
        user.is_superuser or (
            hasattr(user, 'employee_profile') and 
            user.employee_profile.role in ['Manager', 'Admin']
        )
    )

def is_accountant(user):
    return user.is_authenticated and (
        hasattr(user, 'employee_profile') and 
        user.employee_profile.role == 'Accountant'
    )

def is_manager(user):
    """
    Enhanced manager check that:
    1. Handles missing profiles gracefully
    2. Maintains all existing logging
    3. Keeps backward compatibility
    """
    if not user.is_authenticated:
        logger.debug(f"Unauthenticated user access attempt")
        return False
        
    # Superusers should automatically be managers
    if user.is_superuser:
        logger.info(f"Superuser {user.email} granted manager access")
        return True
        
    try:
        # Get or create profile for staff users
        if user.is_staff and not hasattr(user, 'employee_profile'):
            from employee.models import EmployeeProfile
            EmployeeProfile.objects.create(user=user, role='Manager')
            logger.info(f"Created Manager profile for staff user {user.email}")
        
        # Original check with enhanced safety
        is_manager_role = hasattr(user, 'employee_profile') and user.employee_profile.role == 'Manager'
        logger.info(f"Manager check for {user.email}: role={getattr(user.employee_profile, 'role', 'No profile')}, result={is_manager_role}")
        return is_manager_role
        
    except Exception as e:
        logger.error(f"Error checking manager status for {user.email}: {str(e)}", exc_info=True)
        return False  # Fail securely
