# expenses/views/da_settlement.py

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from datetime import date
from accounts.access_control import is_manager
from expenses.models import DailyAllowance
from expenses.services.da_settlement_service import settle_da

def _is_account_manager(user):
    role = getattr(getattr(user, "employeeprofile", None), "role", None) or getattr(user, "role", None)
     return (
        user.has_perm('timesheet.can_approve')
        or is_manager(user)
        or role in {"Account Manager", "Account_Manager"}
    )

def _back_to_da_tab(request):
    nxt = request.POST.get("next")
    if nxt:
        return nxt
    ref = request.META.get("HTTP_REFERER")
    if ref:
        return ref
    return reverse("expenses:unified-expense-dashboard") + "?tab=da"

@login_required
@require_POST
def settle_da_view(request):
    if not _is_account_manager(request.user):
        messages.error(request, "Only Account Manager can settle DA.")
        return redirect(_back_to_da_tab(request))

    da_id = request.POST.get("da_id")
    prefer_adv = request.POST.get("prefer_advance") == "1"
    pay_date_str = request.POST.get("payment_date")

    try:
        pay_date = date.fromisoformat(pay_date_str) if pay_date_str else date.today()
    except Exception:
        pay_date = date.today()

    da = get_object_or_404(DailyAllowance, pk=da_id)
    # record actor for the service (optional)
    da._actor = request.user

    ok, msg = settle_da(da, prefer_advance=prefer_adv, payment_date=pay_date)
    (messages.success if ok else messages.error)(request, msg)
    return redirect(_back_to_da_tab(request))
