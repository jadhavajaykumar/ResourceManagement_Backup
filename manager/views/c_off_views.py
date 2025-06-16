from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from timesheet.models import CompOffApplication
from accounts.access_control import is_manager_or_admin, is_manager
from django.contrib.auth.decorators import login_required, user_passes_test
@user_passes_test(is_manager)
@login_required
def c_off_approvals(request):
    applications = CompOffApplication.objects.all().order_by('-date_requested')
    return render(request, 'manager/c_off_approvals.html', {'applications': applications})

@user_passes_test(is_manager)
@login_required
def approve_c_off(request, application_id):
    app = get_object_or_404(CompOffApplication, pk=application_id)
    app.status = 'Approved'
    app.save()
    return redirect('manager:c-off-approvals')

@user_passes_test(is_manager)
@login_required
def reject_c_off(request, application_id):
    app = get_object_or_404(CompOffApplication, pk=application_id)
    app.status = 'Rejected'
    app.save()
    return redirect('manager:c-off-approvals')
