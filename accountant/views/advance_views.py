from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from expenses.models import AdvanceRequest
from django.contrib import messages
from django.utils import timezone

@login_required
@permission_required('expenses.can_settle')
def accountant_approve_advances(request):
    advances = AdvanceRequest.objects.filter(
        approved_by_manager=True,
        approved_by_accountant=False
    )
    return render(request, 'accountant/approve_advances.html', {'advances': advances})

@login_required
@permission_required('expenses.can_settle')
def accountant_approve_advance(request, advance_id):
    advance = get_object_or_404(
        AdvanceRequest,
        id=advance_id,
        approved_by_manager=True,
        approved_by_accountant=False
    )
    advance.approved_by_accountant = True
    advance.date_approved_by_accountant = timezone.now()
    advance.settled_by_account_manager = False  # Ensure it's clean for next step
    advance.save()

    messages.success(request, 
        f"Advance #{advance_id} approved. Sent to Account Manager for settlement."
    )

    return redirect('accountant:accountant_approve_advances')