from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.access_control import is_manager
from expenses.models import AdvanceRequest
from employee.models import EmployeeProfile
from django.contrib import messages


@login_required
@user_passes_test(is_manager)
def approve_advances(request):
    reportees = EmployeeProfile.objects.filter(reporting_manager=request.user)
    advances = AdvanceRequest.objects.filter(employee__in=reportees, approved_by_manager=False)
    return render(request, 'manager/approve_advances.html', {'advances': advances})

@login_required
@user_passes_test(is_manager)
def approve_advance(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, id=advance_id)
    if advance.approved_by_manager:
        messages.warning(request, f"Advance #{advance_id} is already approved")
        return redirect('manager:approve-advances')
    advance.approved_by_manager = True
    advance.save()
    messages.success(request, 
        f"Advance #{advance_id} approved. Sent to accountant for review."
    )
    return redirect('manager:approve-advances')
    