from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
import logging
from accounts.access_control import is_manager

logger = logging.getLogger(__name__)

@user_passes_test(is_manager)
@login_required
def manager_dashboard(request):
    logger.info(f"Manager dashboard accessed by {request.user.username}, authenticated: {request.user.is_authenticated}")
    return render(request, 'manager/manager_dashboard.html', {})
    