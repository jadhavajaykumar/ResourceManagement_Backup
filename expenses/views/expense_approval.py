# expenses/views/expense_approval.py
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import Expense
from accounts.access_control import is_manager_or_admin


@login_required
def approve_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    if request.user.role in ['Manager', 'Accountant']:
        if 'reject' in request.GET:
            expense.status = 'Rejected'
            messages.success(request, f"Expense {expense.id} rejected.")
        else:
            expense.status = 'Approved'
            messages.success(request, f"Expense {expense.id} approved.")
        expense.save()
    return redirect('expenses:employee-expenses')
