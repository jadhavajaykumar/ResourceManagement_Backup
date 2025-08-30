# account/access_control.py
import logging

logger = logging.getLogger(__name__)
def is_manager_or_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.has_perm('timesheet.can_approve')
    )

def is_manager(user):
    """Check if the user has permission to approve timesheets."""
    return user.is_authenticated and user.has_perm('timesheet.can_approve')


def is_accountant(user):
    """Check if the user has permission to settle expenses."""
    return user.is_authenticated and user.has_perm('expenses.can_settle')


