# expenses/views/unified_actions.py
from datetime import datetime
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db.models import Sum
from expenses.models import Expense, AdvanceRequest, AdvanceAdjustmentLog


def _latest_settled_advance_with_balance(employee):
    """
    Find the latest 'Settled' advance that still has positive remaining balance.

    IMPORTANT: Remaining balance must be computed from AdvanceAdjustmentLog.amount_deducted,
    not from sum of linked Expense.amount (partial deductions are allowed).
    """
    advances = (
        AdvanceRequest.objects
        .filter(employee=employee, status="Settled")
        .order_by("-settlement_date", "-id")
    )
    for adv in advances:
        used_sum = adv.advanceadjustmentlog_set.aggregate(
            total=Sum("amount_deducted")
        )["total"] or 0
        remaining = float(adv.amount) - float(used_sum)
        if remaining > 0:
            return adv, remaining
    return None, 0.0


def _remaining_expense_amount(expense: Expense) -> float:
    """How much of this expense is still uncovered by advances (via logs)."""
    deducted = expense.advanceadjustmentlog_set.aggregate(
        total=Sum("amount_deducted")
    )["total"] or 0
    return float(expense.amount) - float(deducted)


def _adjust_expense_against_latest_advance(expense: Expense):
    """
    Apply *one* latest settled advance to this expense.

    - Adds an AdvanceAdjustmentLog with the deducted amount
    - If fully covered -> reimbursed=True and status='Settled' (stage 'SETTLED' if present)
    - If partial/none  -> status='Approved', reimbursed=False (cash to be paid later)
    """
    # ✅ Use remaining *uncovered* amount (handles previous partial deductions)
    remaining = _remaining_expense_amount(expense)
    if remaining <= 0:
        # Already fully covered by previous logs/advances
        expense.reimbursed = True
        expense.status = "Settled"
        if any(choice[0] == "SETTLED" for choice in Expense.STAGE_CHOICES):
            expense.current_stage = "SETTLED"
        else:
            expense.current_stage = "APPROVED"
        expense.save()
        return

    adv, left = _latest_settled_advance_with_balance(expense.employee)

    if not adv or left <= 0:
        # No advance to consume; AM approval stands, but not reimbursed.
        expense.reimbursed = False
        expense.status = "Approved"
        expense.current_stage = "APPROVED"
        expense.save()
        return

    take = min(remaining, left)

    # Keep linkage for reporting/audits (don't overwrite previous link)
    if expense.advance_used_id is None:
        expense.advance_used = adv

    AdvanceAdjustmentLog.objects.create(
        expense=expense,
        advance=adv,
        amount_deducted=take,
    )

    if take >= remaining:
        # Fully covered by advance -> settled now
        expense.reimbursed = True
        expense.status = "Settled"
        if any(choice[0] == "SETTLED" for choice in Expense.STAGE_CHOICES):
            expense.current_stage = "SETTLED"
        else:
            expense.current_stage = "APPROVED"
    else:
        # Partially covered; remainder needs cash or future advance
        expense.reimbursed = False
        expense.status = "Approved"
        expense.current_stage = "APPROVED"

    expense.save()


def _apply_advance_to_pending_expenses(advance: AdvanceRequest):
    """
    After an advance is SETTLED (credited), consume it against all of the employee's
    already-approved-but-unsettled expenses, oldest first.
    """
    # Compute remaining on this advance from logs (authoritative)
    used_sum = AdvanceAdjustmentLog.objects.filter(advance=advance).aggregate(
        total=Sum("amount_deducted")
    )["total"] or 0
    adv_left = float(advance.amount) - float(used_sum)
    if adv_left <= 0:
        return

    pending = Expense.objects.filter(
        employee=advance.employee,
        status="Approved",
        reimbursed=False
    ).order_by("date", "id")

    for exp in pending:
        if adv_left <= 0:
            break

        remaining = _remaining_expense_amount(exp)
        if remaining <= 0:
            exp.reimbursed = True
            exp.status = "Settled"
            if any(c[0] == "SETTLED" for c in Expense.STAGE_CHOICES):
                exp.current_stage = "SETTLED"
            exp.save(update_fields=["reimbursed", "status", "current_stage"])
            continue

        take = min(remaining, adv_left)

        if exp.advance_used_id is None:
            exp.advance_used = advance

        AdvanceAdjustmentLog.objects.create(
            expense=exp,
            advance=advance,
            amount_deducted=take,
        )

        adv_left -= take
        if take >= remaining:
            exp.reimbursed = True
            exp.status = "Settled"
            if any(c[0] == "SETTLED" for c in Expense.STAGE_CHOICES):
                exp.current_stage = "SETTLED"
            exp.save(update_fields=["advance_used", "reimbursed", "status", "current_stage"])
        else:
            exp.reimbursed = False
            exp.status = "Approved"
            if exp.current_stage != "APPROVED":
                exp.current_stage = "APPROVED"
            exp.save(update_fields=["advance_used", "reimbursed", "status", "current_stage"])


@login_required
def handle_expense_action(request, item_type, item_id, action):
    user = request.user
    role_raw = getattr(user.employeeprofile, "role", "") or ""
    role_key = role_raw.strip().lower().replace(" ", "-")
    remark = request.POST.get("remark", "").strip()

    # fetch object
    if item_type == "expense":
        obj = get_object_or_404(Expense, id=item_id)
    elif item_type == "advance":
        obj = get_object_or_404(AdvanceRequest, id=item_id)
    else:
        messages.error(request, "Invalid item type.")
        return redirect(reverse("expenses:unified-expense-dashboard"))

    # APPROVE
    if action == "approve":
        if item_type == "expense":
            if role_key == "accountant" and obj.current_stage == "ACCOUNTANT":
                obj.current_stage = "MANAGER"
                if hasattr(obj, "accountant_remark"):
                    obj.accountant_remark = remark
                messages.success(request, f"Expense {obj.id} forwarded to Manager.")

            elif role_key == "manager" and obj.current_stage == "MANAGER":
                obj.current_stage = "ACCOUNT_MANAGER"
                if hasattr(obj, "manager_remark"):
                    obj.manager_remark = remark
                messages.success(request, f"Expense {obj.id} forwarded to Account Manager.")

            elif role_key == "account-manager" and obj.current_stage == "ACCOUNT_MANAGER":
                if hasattr(obj, "account_manager_remark"):
                    obj.account_manager_remark = remark
                _adjust_expense_against_latest_advance(obj)
                if obj.reimbursed:
                    messages.success(request, f"Expense {obj.id} settled via available advance.")
                else:
                    messages.info(request, f"Expense {obj.id} approved; remaining will require cash settlement.")
            else:
                messages.warning(request, "Approval action not allowed at this stage for expense.")

        elif item_type == "advance":
            if role_key == "manager" and obj.current_stage == "MANAGER":
                obj.current_stage = "ACCOUNTANT"
                obj.approved_by_manager = True
                obj.status = "Forwarded to Accountant"
                if hasattr(obj, "manager_remark"):
                    obj.manager_remark = remark
                messages.success(request, f"Advance {obj.id} forwarded to Accountant.")

            elif role_key == "accountant" and obj.current_stage == "ACCOUNTANT":
                obj.current_stage = "ACCOUNT_MANAGER"
                obj.approved_by_accountant = True
                obj.date_approved_by_accountant = datetime.now()
                obj.status = "Forwarded to Account Manager"
                if hasattr(obj, "accountant_remark"):
                    obj.accountant_remark = remark
                messages.success(request, f"Advance {obj.id} forwarded to Account Manager.")

            else:
                messages.warning(request, "Approval action not allowed for advance at this stage.")

    # SETTLE (ADVANCE)
    elif action == "settle" and item_type == "advance":
        if role_key == "account-manager" and obj.current_stage == "ACCOUNT_MANAGER":
            date_str = request.POST.get("settlement_date", "").strip()
            try:
                obj.settlement_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Please provide a valid settlement date (YYYY-MM-DD).")
                return redirect(reverse("expenses:unified-expense-dashboard"))

            obj.current_stage = "SETTLED"
            obj.settled_by_account_manager = True
            obj.status = "Settled"
            if hasattr(obj, "account_manager_remark"):
                obj.account_manager_remark = remark
            obj.save()

            # ✅ CRITICAL: auto-apply this credited advance to already-approved expenses
            _apply_advance_to_pending_expenses(obj)

            messages.success(request, f"Advance {obj.id} settled on {obj.settlement_date}. Balance credited.")
            return redirect(reverse("expenses:unified-expense-dashboard"))
        else:
            messages.warning(request, "Only Account Manager can settle the advance at this stage.")

    # SETTLE (EXPENSE) by cash when no advance covers it
    elif action == "settle" and item_type == "expense":
        if role_key == "account-manager":
            if not obj.reimbursed:
                obj.reimbursed = True
                obj.status = "Settled"
                if any(c[0] == "SETTLED" for c in Expense.STAGE_CHOICES):
                    obj.current_stage = "SETTLED"
                if hasattr(obj, "account_manager_remark"):
                    obj.account_manager_remark = remark
                obj.save()
                messages.success(request, f"Expense {obj.id} settled by cash.")
            else:
                messages.info(request, f"Expense {obj.id} is already settled.")
            return redirect(reverse("expenses:unified-expense-dashboard"))
        else:
            messages.warning(request, "Only Account Manager can settle the expense at this stage.")

    # REJECT
    elif action == "reject":
        obj.current_stage = "REJECTED"
        obj.status = "Rejected"
        target_attr = None
        if role_key == "accountant":
            target_attr = "accountant_remark"
        elif role_key == "manager":
            target_attr = "manager_remark"
        elif role_key == "account-manager":
            target_attr = "account_manager_remark"
        if target_attr and hasattr(obj, target_attr):
            setattr(obj, target_attr, remark)
        messages.warning(request, f"{item_type.capitalize()} {obj.id} rejected.")

    else:
        messages.error(request, "Invalid action.")

    obj.save()
    return redirect(reverse("expenses:unified-expense-dashboard"))
