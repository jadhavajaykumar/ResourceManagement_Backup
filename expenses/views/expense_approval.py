# expenses/views/expense_approval.py
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from approvals.models import ApprovalInstance
from expenses.models import Expense
from accounts.access_control import is_accountant, is_manager  # adjust if you have helpers

from django.contrib.contenttypes.models import ContentType

@login_required
@user_passes_test(lambda u: u.has_perm('expenses.can_settle') or u.has_perm('timesheet.can_approve'))
def expense_approval_dashboard(request):
    """
    If you have an additional accountant-facing dashboard template, keep it.
    Otherwise the unified dashboard is primary.
    """
    # Basic listing; keep minimal so you can re-use existing templates
    expenses = Expense.objects.select_related('project', 'employee').filter(
        status__in=["Pending", "Submitted", "Forwarded to Manager", "Forwarded to Account Manager", "Approved"]
    )

    return render(request, 'expenses/expense_approval_dashboard.html', {
        'expenses': expenses,
    })


@login_required
@require_POST
def approve_expense(request, expense_id):
    """
    Approve or reject an expense using the Approval system if one exists, otherwise fallback.
    Query param 'reject' indicates rejection.
    """
    expense = get_object_or_404(Expense, id=expense_id)

    if not (request.user.has_perm("expenses.can_settle") or request.user.has_perm("timesheet.can_approve")):
        messages.error(request, "You are not authorized to approve expenses.")
        return redirect("expenses:unified-expense-dashboard")

    ctype = ContentType.objects.get_for_model(Expense)
    inst = ApprovalInstance.objects.filter(content_type=ctype, object_id=expense.id, finished=False).first()

    if not inst:
        # fallback/backward compatibility: update expense directly
        if "reject" in request.GET:
            expense.status = "Rejected"
            messages.success(request, f"Expense {expense.id} rejected (no approval instance).")
        else:
            expense.status = "Approved"
            messages.success(request, f"Expense {expense.id} approved (no approval instance).")
        expense.save()
        return redirect("expenses:unified-expense-dashboard")

    action_slug = "reject" if "reject" in request.GET else "approve"

    try:
        ok, msg = inst.apply_action(request.user, action_slug, remark="Via UI")
        if not ok:
            messages.error(request, msg)
        else:
            messages.success(request, msg)
    except Exception as e:
        messages.error(request, str(e))

    return redirect("expenses:unified-expense-dashboard")

