from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from collections import defaultdict
from utils.currency import format_currency


from expenses.models import Expense, DailyAllowance
from accountant.services.approval_flow import process_expense_action
from accountant.views.common import is_accountant

from django.utils import timezone

from project.models import Project
from employee.models import EmployeeProfile

@login_required
@user_passes_test(is_accountant)
def expense_approval_dashboard(request):
    # Get filters
    selected_project = request.GET.get('project')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # Base querysets
    expenses = Expense.objects.select_related('project', 'employee').all()
    allowances = DailyAllowance.objects.select_related('project', 'employee').all()

    # Apply filters
    if selected_project and selected_project != "all":
        expenses = expenses.filter(project_id=selected_project)
        allowances = allowances.filter(project_id=selected_project)
    if from_date:
        expenses = expenses.filter(date__gte=from_date)
        allowances = allowances.filter(date__gte=from_date)
    if to_date:
        expenses = expenses.filter(date__lte=to_date)
        allowances = allowances.filter(date__lte=to_date)

    # Categorize
    tabbed_expenses = {
        'pending': [],
        'approved': [],
        'reimbursement': [],
        'settled': []
    }

    for expense in expenses:
        entry = {
            "type": "Expense",
            "employee": expense.employee,
            "project": expense.project,
            "amount": format_currency(expense.amount, getattr(expense, 'currency', 'INR')),
            "date": expense.date,
            "status": expense.status,
            "reimbursed": expense.reimbursed,
            "new_expense_type": expense.new_expense_type,
            "id": expense.id,
        }

        if expense.status == "Pending":
            tabbed_expenses["pending"].append(entry)
        elif expense.status == "Approved" and not expense.reimbursed:
            tabbed_expenses["reimbursement"].append(entry)
        elif expense.status == "Approved" and expense.reimbursed:
            tabbed_expenses["settled"].append(entry)
        else:
            tabbed_expenses["approved"].append(entry)


    for da in allowances:
        entry = {
            "type": "DA",
            "employee": da.employee,
            "project": da.project,
            "amount": format_currency(da.da_amount, da.currency),
            "currency": da.currency,
            "date": da.date,
            "status": "Approved" if da.approved else "Pending",
            "reimbursed": da.reimbursed,
            "id": da.id,
            "approved": da.approved,
        }

        if not da.approved:
            tabbed_expenses["pending"].append(entry)
        elif da.approved and not da.reimbursed:
            tabbed_expenses["reimbursement"].append(entry)
        elif da.approved and da.reimbursed:
            tabbed_expenses["settled"].append(entry)
        else:
            tabbed_expenses["approved"].append(entry)

    # Get project list for filters
    projects = Expense.objects.values('project__id', 'project__name').distinct()

    return render(request, 'accountant/expense_approval_dashboard.html', {
        'tabbed_expenses': tabbed_expenses,
        'tab_names': ["pending", "approved", "reimbursement", "settled"],
        'projects': projects,
    })




@require_POST
@login_required
@user_passes_test(is_accountant)
def approve_or_reject_expense(request, expense_id, action):
    expense = get_object_or_404(Expense, id=expense_id)
    remark = request.POST.get("remark", "").strip()

    if not remark:
        messages.error(request, "Remark is required for both approval and rejection.")
        return redirect('accountant:expense-approval')

    if expense.status == 'Pending':
        process_expense_action(expense, action, remark, request)

    return redirect('accountant:expense-approval')


@login_required
@user_passes_test(is_accountant)
def approve_daily_allowance(request, da_id):
    da = get_object_or_404(DailyAllowance, id=da_id)

    if not da.approved:
        da.approved = True
        da.save()
        messages.success(request, f"DA for {da.employee.user.get_full_name()} on {da.date} approved.")
    else:
        messages.info(request, "DA is already approved.")

    return redirect('accountant:expense-approval')
