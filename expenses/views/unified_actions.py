# expenses/views/unified_actions.py
from datetime import datetime
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db.models import Sum
from django.db import transaction

from expenses.models import Expense, AdvanceRequest, AdvanceAdjustmentLog
from employee.models import EmployeeProfile

# helpers

def _role_key_for_user(user):
    """Normalise user's role (from employeeprofile.role or user.role)."""
    ep = getattr(user, "employeeprofile", None)
    role_raw = getattr(ep, "role", None) or getattr(user, "role", None) or ""
    return role_raw.strip().lower().replace(" ", "-")

def _latest_settled_advance_with_balance(employee):
    """
    Return (advance_obj, remaining_balance) for the latest Settled advance with remaining positive balance.
    """
    advances = (
        AdvanceRequest.objects
        .filter(employee=employee, status="Settled")
        .order_by("-settlement_date", "-id")
    )
    for adv in advances:
        used_sum = adv.advanceadjustmentlog_set.aggregate(total=Sum("amount_deducted"))["total"] or 0
        remaining = float(adv.amount) - float(used_sum)
        if remaining > 0:
            return adv, remaining
    return None, 0.0


def _remaining_expense_amount(expense: Expense) -> float:
    """How much of this expense is still uncovered by advances (via logs)."""
    deducted = expense.advanceadjustmentlog_set.aggregate(total=Sum("amount_deducted"))["total"] or 0
    return float(expense.amount) - float(deducted)


def _adjust_expense_against_latest_advance(expense: Expense):
    """
    Apply the latest settled advance to the provided expense (one-time attempt).
    Adds AdvanceAdjustmentLog and updates expense.reimbursed/status/current_stage accordingly.
    """
    remaining = _remaining_expense_amount(expense)
    if remaining <= 0:
        expense.reimbursed = True
        expense.status = "Settled"
        expense.current_stage = getattr(expense, "current_stage", "APPROVED")
        expense.save()
        return

    adv, left = _latest_settled_advance_with_balance(expense.employee)
    if not adv or left <= 0:
        # No advance available
        expense.reimbursed = False
        expense.status = "Approved"
        expense.current_stage = "APPROVED"
        expense.save()
        return

    take = min(remaining, left)

    if expense.advance_used_id is None:
        expense.advance_used = adv

    # create adjustment log and update
    AdvanceAdjustmentLog.objects.create(
        expense=expense,
        advance=adv,
        amount_deducted=take,
    )

    if take >= remaining:
        expense.reimbursed = True
        expense.status = "Settled"
        expense.current_stage = "SETTLED" if any(c[0] == "SETTLED" for c in getattr(Expense, "STAGE_CHOICES", [])) else "APPROVED"
    else:
        expense.reimbursed = False
        expense.status = "Approved"
        expense.current_stage = "APPROVED"

    expense.save()


@login_required
def handle_expense_action(request, item_type, item_id, action):
    """
    Unified action endpoint for expenses/advances.
    item_type: 'expense' or 'advance'
    action: 'approve', 'reject', 'settle'
    """
    user = request.user
    role_key = _role_key_for_user(user)
    remark = (request.POST.get("remark") or "").strip()

    # fetch object
    if item_type == "expense":
        obj = get_object_or_404(Expense, id=item_id)
    elif item_type == "advance":
        obj = get_object_or_404(AdvanceRequest, id=item_id)
    else:
        messages.error(request, "Invalid item type.")
        return redirect(reverse("expenses:unified-expense-dashboard"))
        
    try:
        from approvals.utils import get_instance_for_object, user_matches_selector
        from approvals.services import perform_action_on_instance

        inst = get_instance_for_object(obj)
    except Exception:
        inst = None

    if inst:
        step = inst.current_step()
        if not step:
            messages.error(request, "Approval process already finished or misconfigured.")
            return redirect(reverse("expenses:unified-expense-dashboard"))

        if not user_matches_selector(user, step.selector_type, step.selector_value):
            messages.error(request, "You are not authorized to act at this step.")
            return redirect(reverse("expenses:unified-expense-dashboard"))

        if action == "approve":
            if not remark:
                messages.error(request, "Please provide an approval remark.")
                return redirect(reverse("expenses:unified-expense-dashboard"))
            inst = perform_action_on_instance(inst, "approve", actor=user, remark=remark)
            if inst.finished and inst.result == "APPROVED":
                if item_type == "expense":
                    _adjust_expense_against_latest_advance(obj)
                    if not obj.reimbursed:
                        obj.status = "Approved"
                elif item_type == "advance":
                    obj.status = "Forwarded to Account Manager"
                obj.save()
                messages.success(request, f"{item_type.capitalize()} {obj.id} fully approved via flow.")
            else:
                messages.success(request, f"{item_type.capitalize()} {obj.id} forwarded to next approver.")
            return redirect(reverse("expenses:unified-expense-dashboard"))

        elif action == "reject":
            if not remark:
                messages.error(request, "Please provide a rejection remark.")
                return redirect(reverse("expenses:unified-expense-dashboard"))
            inst = perform_action_on_instance(inst, "reject", actor=user, remark=remark)
            obj.current_stage = "REJECTED"
            obj.status = "Rejected"
            obj.save()
            messages.warning(request, f"{item_type.capitalize()} {obj.id} rejected.")
            return redirect(reverse("expenses:unified-expense-dashboard"))

        else:
            messages.error(request, "Invalid action for approvals flow.")
            return redirect(reverse("expenses:unified-expense-dashboard"))    

    # Keep changes atomic where multiple writes happen
    try:
        with transaction.atomic():
            # ------------------- APPROVE -------------------
            if action == "approve":
                if item_type == "expense":
                    # Flow: Accountant -> Manager -> Account Manager (AM settles)
                    if role_key == "accountant" and getattr(obj, "current_stage", "") == "ACCOUNTANT":
                        obj.current_stage = "MANAGER"
                        if hasattr(obj, "accountant_remark") and remark:
                            obj.accountant_remark = remark
                        obj.save()
                        messages.success(request, f"Expense {obj.id} forwarded to Manager.")
                    elif role_key == "manager" and getattr(obj, "current_stage", "") == "MANAGER":
                        obj.current_stage = "ACCOUNT_MANAGER"
                        if hasattr(obj, "manager_remark") and remark:
                            obj.manager_remark = remark
                        obj.save()
                        messages.success(request, f"Expense {obj.id} forwarded to Account Manager.")
                    elif role_key in ("account-manager", "account_manager") and getattr(obj, "current_stage", "") == "ACCOUNT_MANAGER":
                        # Final approver (AM) — attempt settle via available advance
                        if hasattr(obj, "account_manager_remark") and remark:
                            obj.account_manager_remark = remark
                        elif remark:
                            # fallback into manager_remark to retain audit trail
                            obj.manager_remark = (obj.manager_remark or "") + f"\n[AM Remark] {remark}"
                        # Try to apply advance -> this will update status (Approved/Settled)
                        _adjust_expense_against_latest_advance(obj)
                        messages.success(request, f"Expense {obj.id} processed by Account Manager.")
                    else:
                        messages.warning(request, "Approval action not allowed at this stage for this expense.")
                elif item_type == "advance":
                    # Advance approval flow (Manager -> Accountant -> Account Manager to settle)
                    if role_key == "manager" and getattr(obj, "current_stage", "") == "MANAGER":
                        obj.current_stage = "ACCOUNTANT"
                        obj.approved_by_manager = True
                        obj.status = "Forwarded to Accountant"
                        if hasattr(obj, "manager_remark") and remark:
                            obj.manager_remark = remark
                        obj.save()
                        messages.success(request, f"Advance {obj.id} forwarded to Accountant.")
                    elif role_key == "accountant" and getattr(obj, "current_stage", "") == "ACCOUNTANT":
                        obj.current_stage = "ACCOUNT_MANAGER"
                        obj.approved_by_accountant = True
                        obj.date_approved_by_accountant = datetime.now()
                        obj.status = "Forwarded to Account Manager"
                        if hasattr(obj, "accountant_remark") and remark:
                            obj.accountant_remark = remark
                        obj.save()
                        messages.success(request, f"Advance {obj.id} forwarded to Account Manager.")
                    else:
                        messages.warning(request, "Approval action not allowed for advance at this stage.")
                else:
                    messages.error(request, "Invalid item type for approve.")
                # end approve

            # ------------------- SETTLE -------------------
            elif action == "settle":
                if item_type == "advance":
                    # Account Manager marks advance as settled and then apply advance to pending expenses
                    if role_key in ("account-manager", "account_manager") and getattr(obj, "current_stage", "") == "ACCOUNT_MANAGER":
                        date_str = request.POST.get("settlement_date", "").strip()
                        try:
                            obj.settlement_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        except Exception:
                            messages.error(request, "Please provide a valid settlement date (YYYY-MM-DD).")
                            return redirect(reverse("expenses:unified-expense-dashboard"))

                        obj.current_stage = "SETTLED"
                        obj.settled_by_account_manager = True
                        obj.status = "Settled"
                        if hasattr(obj, "account_manager_remark") and remark:
                            obj.account_manager_remark = remark
                        obj.save()

                        # Apply credited advance to already-approved pending expenses
                        # (Implementing function below or reusing existing)
                        # We reuse logic similar to your previous _apply_advance_to_pending_expenses
                        from .unified_actions import _apply_advance_to_pending_expenses  # if in same module, else implement below
                        try:
                            _apply_advance_to_pending_expenses(obj)
                        except Exception:
                            # avoid breaking the view — log & continue
                            pass

                        messages.success(request, f"Advance {obj.id} settled on {obj.settlement_date}.")
                    else:
                        messages.warning(request, "Only Account Manager can settle the advance at this stage.")
                elif item_type == "expense":
                    # Cash settlement for expense by Account Manager
                    if role_key in ("account-manager", "account_manager"):
                        date_str = request.POST.get("settlement_date", "").strip()
                        if not date_str:
                            messages.error(request, "Please provide a settlement date.")
                            return redirect(reverse("expenses:unified-expense-dashboard"))
                        try:
                            dt = datetime.strptime(date_str, "%Y-%m-%d")
                        except Exception:
                            messages.error(request, "Please provide a valid settlement date (YYYY-MM-DD).")
                            return redirect(reverse("expenses:unified-expense-dashboard"))

                        if not obj.reimbursed:
                            obj.reimbursed = True
                            obj.status = "Settled"
                            obj.current_stage = "SETTLED" if any(c[0] == "SETTLED" for c in getattr(Expense, "STAGE_CHOICES", [])) else "APPROVED"
                            # store remark in account_manager_remark or fallback to manager_remark
                            if hasattr(obj, "account_manager_remark") and remark:
                                existing = obj.account_manager_remark or ""
                                obj.account_manager_remark = f"{existing}\n[Cash Settled {date_str}] {remark}".strip()
                            elif remark:
                                existing = obj.manager_remark or ""
                                obj.manager_remark = f"{existing}\n[AM Cash Settled {date_str}] {remark}".strip()
                            obj.manager_reviewed_at = dt
                            obj.save()
                            messages.success(request, f"Expense {obj.id} settled by cash on {date_str}.")
                        else:
                            messages.info(request, f"Expense {obj.id} is already settled.")
                    else:
                        messages.warning(request, "Only Account Manager can settle expense by cash.")
                else:
                    messages.error(request, "Settle is only valid for advance or expense.")

            # ------------------- REJECT -------------------
            elif action == "reject":
                # When rejected, move to REJECTED state and persist remark appropriately
                if item_type == "expense":
                    obj.current_stage = "REJECTED"
                    obj.status = "Rejected"
                    if role_key == "accountant" and hasattr(obj, "accountant_remark"):
                        obj.accountant_remark = remark
                    elif role_key == "manager" and hasattr(obj, "manager_remark"):
                        obj.manager_remark = remark
                    elif role_key in ("account-manager", "account_manager") and hasattr(obj, "account_manager_remark"):
                        obj.account_manager_remark = remark
                    else:
                        # fallback append into manager_remark to capture rejection note
                        existing = getattr(obj, "manager_remark", "") or ""
                        obj.manager_remark = f"{existing}\n[Rejected by {role_key}] {remark}".strip()
                    obj.save()
                    messages.warning(request, f"Expense {obj.id} rejected.")
                elif item_type == "advance":
                    obj.current_stage = "REJECTED"
                    obj.status = "Rejected"
                    # persist remark where appropriate
                    if role_key == "manager" and hasattr(obj, "manager_remark"):
                        obj.manager_remark = remark
                    elif role_key == "accountant" and hasattr(obj, "accountant_remark"):
                        obj.accountant_remark = remark
                    elif role_key in ("account-manager", "account_manager") and hasattr(obj, "account_manager_remark"):
                        obj.account_manager_remark = remark
                    else:
                        existing = getattr(obj, "manager_remark", "") or ""
                        obj.manager_remark = f"{existing}\n[Rejected by {role_key}] {remark}".strip()
                    obj.save()
                    messages.warning(request, f"Advance {obj.id} rejected.")
                else:
                    messages.error(request, "Invalid item for rejection.")

            else:
                messages.error(request, "Invalid action.")
    except Exception as exc:
        # Log or re-raise as needed
        messages.error(request, f"Action failed: {exc}")

    return redirect(reverse("expenses:unified-expense-dashboard"))


# --------------------------------------------------------------
# Support function used by settle-advance: apply credited advance to pending expenses
# (Kept in same file for drop-in convenience; if you already have this earlier, you can remove duplicate)
def _apply_advance_to_pending_expenses(advance: AdvanceRequest):
    used_sum = AdvanceAdjustmentLog.objects.filter(advance=advance).aggregate(total=Sum("amount_deducted"))["total"] or 0
    adv_left = float(advance.amount) - float(used_sum)
    if adv_left <= 0:
        return

    pending = Expense.objects.filter(employee=advance.employee, status="Approved", reimbursed=False).order_by("date", "id")

    for exp in pending:
        if adv_left <= 0:
            break
        remaining = _remaining_expense_amount(exp)
        if remaining <= 0:
            exp.reimbursed = True
            exp.status = "Settled"
            exp.current_stage = "SETTLED" if any(c[0] == "SETTLED" for c in getattr(Expense, "STAGE_CHOICES", [])) else "APPROVED"
            exp.save(update_fields=["reimbursed", "status", "current_stage"])
            continue

        take = min(remaining, adv_left)
        if exp.advance_used_id is None:
            exp.advance_used = advance

        AdvanceAdjustmentLog.objects.create(expense=exp, advance=advance, amount_deducted=take)
        adv_left -= take

        if take >= remaining:
            exp.reimbursed = True
            exp.status = "Settled"
            exp.current_stage = "SETTLED" if any(c[0] == "SETTLED" for c in getattr(Expense, "STAGE_CHOICES", [])) else "APPROVED"
        else:
            exp.reimbursed = False
            exp.status = "Approved"
            exp.current_stage = "APPROVED"
        exp.save(update_fields=["advance_used", "reimbursed", "status", "current_stage"])
