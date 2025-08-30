from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from accountmanager.views.common import is_accountmanager
from expenses.models import Expense, DailyAllowance, AdvanceRequest, AdvanceAdjustmentLog
from django.utils.timezone import now
from django.contrib import messages
from django.db.models import Sum
import logging

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_accountmanager)
def settle_advances(request):
    # Get advances approved by both manager and accountant but not settled
    advances = AdvanceRequest.objects.filter(
        approved_by_manager=True,
        approved_by_accountant=True,  # Requires accountant approval
        settled_by_account_manager=False
    )
    logger.info(f"[AccountManager] Found {advances.count()} advances ready for settlement.")
    return render(request, 'accountmanager/settle_advances.html', {'advances': advances})


@login_required
@user_passes_test(is_accountmanager)
def settle_advance(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, id=advance_id)

    if not advance.approved_by_manager or not advance.approved_by_accountant:
        messages.error(request, "Cannot settle an advance that hasn't been fully approved")
        return redirect('accountmanager:settle-advances')

    # 🔍 Look for most recent settled advance (if any)
    previous_advances = AdvanceRequest.objects.filter(
        employee=advance.employee,
        settled_by_account_manager=True
    ).exclude(id=advance.id).order_by('-settlement_date')

    deduction_notice = ""
    adjusted_amount = advance.amount

    if previous_advances.exists():
        latest_prev = previous_advances.first()
        used_sum = latest_prev.used_expenses.aggregate(Sum("amount"))['amount__sum'] or 0
        prev_balance = float(latest_prev.amount) - float(used_sum)

        # ✅ Negative balance detected – log and reduce new advance
        if prev_balance < 0:
            adjusted_amount = float(advance.amount) + float(prev_balance)  # balance is negative
            if adjusted_amount < 0:
                adjusted_amount = 0

            # Log this deduction
            AdvanceAdjustmentLog.objects.create(
                expense=None,
                advance=advance,
                amount_deducted=abs(prev_balance)
            )

            logger.info(f"Advance #{advance.id} adjusted by {abs(prev_balance)} due to carry-forward negative balance.")
            deduction_notice = f" (adjusted by ₹{abs(prev_balance):.2f} due to negative balance)"

    advance.adjusted_amount = adjusted_amount
    advance.settled_by_account_manager = True
    advance.settlement_date = now().date()
    advance.save()

    messages.success(
        request,
        f"Advance of ₹{adjusted_amount:.2f} settled for {advance.employee.user.get_full_name()}{deduction_notice}"
    )

    return redirect('accountmanager:settle-advances')
