# expenses/views/expense_approval.py
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from ..models import Expense



@login_required
@user_passes_test(lambda u: u.has_perm('expenses.can_settle') or u.has_perm('timesheet.can_approve'))
def approve_expense(request, expense_id):
    """Approve or reject an expense and redirect to the unified dashboard."""
    expense = get_object_or_404(Expense, id=expense_id)
    if request.user.has_perm('expenses.can_settle') or request.user.has_perm('timesheet.can_approve'):
        if 'reject' in request.GET:
            expense.status = 'Rejected'
            messages.success(request, f"Expense {expense.id} rejected.")
        else:
            expense.status = 'Approved'
            messages.success(request, f"Expense {expense.id} approved.")
        expense.save()
    # Redirect back to the unified expense dashboard after handling the expense
    return redirect("expenses:unified-expense-dashboard")