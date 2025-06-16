# account/access_control.py
import logging
from accounts.utils import get_effective_role

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
    """Check if user has Manager role."""
    return _check_role(user, 'Manager')

def is_hr(user):
    """Check if user has HR role."""
    return _check_role(user, 'HR')

def is_accountant(user):
    """Check if user has Accountant role."""
    return _check_role(user, 'Accountant')

def is_employee(user):
    """Check if user has Employee role."""
    return _check_role(user, 'Employee')

def is_director(user):
    """Check if user has Director role."""
    return _check_role(user, 'Director')

def is_admin(user):
    """Check if user is Django admin (superuser)."""
    if user.is_authenticated and user.is_superuser:
        logger.info(f"Superuser {user.email} granted Admin access")
        return True
    return False

def _check_role(user, expected_role):
    """
    Generic role check with logging.
    Uses get_effective_role() to avoid direct model access.
    """
    if not user.is_authenticated:
        logger.debug("Unauthenticated user access attempt")
        return False

    try:
        role = get_effective_role(user)
        has_role = role == expected_role
        logger.info(f"Role check for {user.email}: expected={expected_role}, actual={role}, result={has_role}")
        return has_role
    except Exception as e:
        logger.error(f"Error checking role for {user.email}: {str(e)}", exc_info=True)
        return False
