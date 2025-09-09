# expenses/views/expense_approval.py
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST

from expenses.models import Expense
from accounts.access_control import is_accountant, is_manager  # adjust if you have helpers


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
    Simple approve/reject endpoint used by some parts of the app.
    Permissions: users with 'expenses.can_settle' OR 'timesheet.can_approve' may act.
    Query param 'reject' indicates rejection.
    """
    expense = get_object_or_404(Expense, id=expense_id)
    if not (request.user.has_perm('expenses.can_settle') or request.user.has_perm('timesheet.can_approve')):
        messages.error(request, "You are not authorized to approve expenses.")
        return redirect("expenses:unified-expense-dashboard")

    if 'reject' in request.GET:
        expense.status = 'Rejected'
        messages.success(request, f"Expense {expense.id} rejected.")
    else:
        expense.status = 'Approved'
        messages.success(request, f"Expense {expense.id} approved.")
    expense.save()
    return redirect("expenses:unified-expense-dashboard")
