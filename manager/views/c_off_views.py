from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from timesheet.models import CompOffApplication
from django.contrib.auth.decorators import login_required, permission_required


@login_required
@permission_required('timesheet.can_approve')
def c_off_approvals(request):
    applications = CompOffApplication.objects.all().order_by('-date_requested')
    return render(request, 'manager/c_off_approvals.html', {'applications': applications})

@login_required
@permission_required('timesheet.can_approve')
def approve_c_off(request, application_id):
    app = get_object_or_404(CompOffApplication, pk=application_id)
    app.status = 'Approved'
    app.save()
    return redirect('manager:c-off-approvals')

@login_required
@permission_required('timesheet.can_approve')
def reject_c_off(request, application_id):
    app = get_object_or_404(CompOffApplication, pk=application_id)
    app.status = 'Rejected'
    app.save()
    return redirect('manager:c-off-approvals')