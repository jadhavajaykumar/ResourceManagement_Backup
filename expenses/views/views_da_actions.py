# expenses/views/views_da_actions.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, resolve_url
from expenses.models import DailyAllowance
from django.urls import reverse

def _back_to_dashboard(request):
    # 1) honor explicit next from the form (best UX, keeps you on DA tab)
    next_url = request.POST.get("next")
    if next_url:
        return next_url

    # 2) otherwise use referer if available
    referer = request.META.get("HTTP_REFERER")
    if referer:
        return referer

    # 3) final fallback: unified dashboard with DA tab selected
    return reverse("expenses:unified-expense-dashboard") + "?tab=da"

def _can_review(user):
    role = getattr(getattr(user, "employeeprofile", None), "role", None) or getattr(user, "role", None)
    return user.is_staff or role in {"Manager", "Accountant", "Account Manager", "Account_Manager"}
    
# granular role checks
def _is_manager(user):
    role = getattr(getattr(user, "employeeprofile", None), "role", None) or getattr(user, "role", None)
    return role == "Manager"

def _is_accountant(user):
    role = getattr(getattr(user, "employeeprofile", None), "role", None) or getattr(user, "role", None)
    return role == "Accountant"

def _is_account_manager(user):
    role = getattr(getattr(user, "employeeprofile", None), "role", None) or getattr(user, "role", None)
    return role in {"Account Manager", "Account_Manager"}    
    
    

def _is_weekend_auto(da):
    return da.is_weekend and da.auto_generated and da.timesheet_id is None

@login_required
@require_POST
def approve_weekend_da(request, pk):
    da = get_object_or_404(DailyAllowance, pk=pk)

    # ✅ Only Manager can approve
    if not _is_manager(request.user) or not _is_weekend_auto(da):
        messages.error(request, "You are not allowed to approve this DA.")
        return redirect(_back_to_dashboard(request))

    # do nothing if already decided
    if da.approved or getattr(da, "rejected", False):
        messages.info(request, "This DA has already been decided.")
        return redirect(_back_to_dashboard(request))

    # mark approved
    if hasattr(da, "mark_approved"):
        da.mark_approved(user=request.user, remark="Manager approved.")
    else:
        da.approved = True
        if hasattr(da, "rejected"):
            da.rejected = False
        da.save(update_fields=["approved"] + (["rejected"] if hasattr(da, "rejected") else []))

    # 🔁 Immediately attempt to settle against advance (preferred)
    try:
        ok, msg = settle_da(da, prefer_advance=True, payment_date=None)
        if ok:
            messages.success(request, f"Weekend DA approved and settled: {msg}")
        else:
            # No advance available; DA remains for cash reimbursement workflow
            messages.success(request, "Weekend DA approved. No advance available; pending cash settlement.")
    except Exception as e:
        messages.warning(request, f"Weekend DA approved, but settlement check failed: {e}")

    return redirect(_back_to_dashboard(request))

@login_required
@require_POST
def reject_weekend_da(request, pk):
    da = get_object_or_404(DailyAllowance, pk=pk)

    # ✅ Only Manager can reject
    if not _is_manager(request.user) or not _is_weekend_auto(da):
        messages.error(request, "You are not allowed to reject this DA.")
        return redirect(_back_to_dashboard(request))

    # do nothing if already decided
    if da.approved or getattr(da, "rejected", False):
        messages.info(request, "This DA has already been decided.")
        return redirect(_back_to_dashboard(request))

    if hasattr(da, "mark_rejected"):
        da.mark_rejected(user=request.user, remark="Manager rejected.")
    else:
        da.approved = False
        if hasattr(da, "rejected"):
            da.rejected = True
            da.save(update_fields=["approved", "rejected"])
        else:
            da.save(update_fields=["approved"])

    messages.info(request, "Weekend DA rejected.")
    return redirect(_back_to_dashboard(request))

@login_required
@require_POST
def delete_weekend_da(request, pk):
    da = get_object_or_404(DailyAllowance, pk=pk)

    # ✅ Accountant can delete ONLY when pending; Manager can also delete when pending
    allowed = (_is_accountant(request.user) or _is_manager(request.user))
    if not allowed or not _is_weekend_auto(da):
        messages.error(request, "You are not allowed to delete this DA.")
        return redirect(_back_to_dashboard(request))

    # delete only if still pending (disabled after manager decision)
    if da.approved or getattr(da, "rejected", False):
        messages.error(request, "This DA has already been decided and cannot be deleted.")
        return redirect(_back_to_dashboard(request))

    da.delete()
    messages.warning(request, "Weekend DA deleted.")
    return redirect(_back_to_dashboard(request))

