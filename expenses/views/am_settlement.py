# expenses/views/am_settlement.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.urls import reverse
from employee.models import EmployeeProfile
from expenses.services.settlement_summary import build_unsettled_summary, settle_everything_for_employee
from accounts.access_control import is_manager


def _is_account_manager(user):
    role = getattr(getattr(user, "employeeprofile", None), "role", None) or getattr(user, "role", None)
    return bool(
        user.has_perm("timesheet.can_approve")
        or is_manager(user)
        or role in ["Account Manager", "Account_Manager"]
    )


@login_required
def am_unsettled_summary(request):
    if not _is_account_manager(request.user):
        messages.error(request, "Only Account Manager can view settlements.")
        return redirect("expenses:unified-expense-dashboard")

    summary = build_unsettled_summary()
    rows = [
        {
            "employee": emp,
            "total_expenses": data["total_expenses"],
            "total_da": data["total_da"],
            "grand_total": data["grand_total"],
        }
        for emp, data in summary.items()
    ]

    return render(
        request,
        "expenses/am_unsettled_summary.html",
        {
            "rows": rows,
            "today": now().date(),
        },
    )


@login_required
@require_POST
def am_bulk_settle_employee(request, employee_id):
    """
    Bulk-settle for a single employee:
      - uses your service `settle_everything_for_employee`
      - honors ?next=... (or hidden 'next') to return to unified dashboard 'am' tab
      - otherwise falls back to AM summary page
    """
    if not _is_account_manager(request.user):
        messages.error(request, "Only Account Manager can settle.")
        return redirect("expenses:unified-expense-dashboard")

    # respect optional 'next' field so the unified tab flow works
    next_url = request.POST.get("next")

    emp = get_object_or_404(EmployeeProfile, pk=employee_id)
    pay_date_str = request.POST.get("payment_date")  # optional
    try:
        from datetime import date
        payment_date = date.fromisoformat(pay_date_str) if pay_date_str else now().date()
    except Exception:
        payment_date = now().date()

    ok, msg, _ = settle_everything_for_employee(emp, payment_date=payment_date)
    (messages.success if ok else messages.error)(request, msg)

    if next_url:
        return redirect(next_url)
    return redirect("expenses:am-unsettled-summary")
