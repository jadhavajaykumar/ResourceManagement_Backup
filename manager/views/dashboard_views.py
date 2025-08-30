from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
import logging

logger = logging.getLogger(__name__)

@login_required
@permission_required('timesheet.can_approve')
def manager_dashboard(request):
    logger.info(f"Manager dashboard accessed by {request.user.username}, authenticated: {request.user.is_authenticated}")
    return render(request, 'manager/manager_dashboard.html', {})