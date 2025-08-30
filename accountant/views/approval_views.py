from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from collections import defaultdict
from django.db.models import Sum
from expenses.models import AdvanceAdjustmentLog

from utils.currency import format_currency
import io
import xlsxwriter
from django.http import HttpResponse
from django.utils.timezone import localtime
from expenses.models import AdvanceRequest
from expenses.models import Expense, DailyAllowance
from accountant.services.approval_flow import process_expense_action
from accountant.views.common import is_accountant
from django.utils import timezone
from project.models import Project
from employee.models import EmployeeProfile
from .advance_views import accountant_approve_advance
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('expenses.can_settle')
def expense_approval_dashboard(request):
    selected_project = request.GET.get('project')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    expenses = Expense.objects.select_related('project', 'employee').filter(status__in=["Pending", "Submitted", "Forwarded to Manager", "Approved", "Rejected"])
    allowances = DailyAllowance.objects.select_related('project', 'employee').all()
    advance_requests = AdvanceRequest.objects.select_related('employee', 'project').filter(
        approved_by_manager=True,
        approved_by_accountant=False
    )

    if selected_project and selected_project != "all":
        expenses = expenses.filter(project_id=selected_project)
        allowances = allowances.filter(project_id=selected_project)
        advance_requests = advance_requests.filter(project_id=selected_project)

    if from_date:
        expenses = expenses.filter(date__gte=from_date)
        allowances = allowances.filter(date__gte=from_date)
        advance_requests = advance_requests.filter(date_requested__gte=from_date)

    if to_date:
        expenses = expenses.filter(date__lte=to_date)
        allowances = allowances.filter(date__lte=to_date)
        
        entry = {
            "type": "Advance",
            "employee": adv.employee,
            "project": adv.project,
            "amount": format_currency(adv.amount, 'INR'),
            "date": adv.date_requested,
            "status": "Pending",
            "reimbursed": False,
            "id": adv.id,
            "purpose": adv.purpose,
            "approved_by_manager": adv.approved_by_manager,
            "approved_by_accountant": adv.approved_by_accountant,
        }
        tabbed_expenses["advance"].append(entry)

    projects = Expense.objects.values('project__id', 'project__name').distinct()

    return render(request, 'accountant/expense_approval_dashboard.html', {
        'tabbed_expenses': tabbed_expenses,
        'tab_names': ["submitted", "approved", "reimbursement", "settled", "advance"],
        'projects': projects,
    })


@login_required
@permission_required('expenses.can_settle')
@require_POST
def approve_or_reject_expense(request, expense_id, action):
    expense = get_object_or_404(Expense, id=expense_id)
    expenses = Expense.objects.select_related('project', 'employee').filter(
        status__in=["Submitted", "Forwarded to Manager", "Forwarded to Account Manager", "Approved", "Rejected"]
    )

    if action == "approve":
        expense.status = "Forwarded to Manager"
        expense.forwarded_to_manager = True
        expense.forwarded_to_accountmanager = False
        expense.save()
        messages.success(request, f"Expense {expense.id} forwarded to Manager.")

        if expense.advance_used is None:
            latest_advance = (
                AdvanceRequest.objects.filter(
                    employee=expense.employee,
                    settled_by_account_manager=True
                )
                .order_by('-settlement_date')
                .first()
            )

            if latest_advance:

                    messages.success(
                        request,
                        f"Expense ID {expense.id} approved and fully deducted ₹{expense.amount} from Advance ID {latest_advance.id}."
                    )
            else:
                expense.save()
                messages.success(request, f"Expense ID {expense.id} approved with no advance available for deduction.")
        else:
            expense.save()
            messages.success(request, f"Expense ID {expense.id} approved and already linked to Advance ID {expense.advance_used.id}.")

    elif action == "reject":
        expense.status = "Rejected"
        expense.forwarded_to_manager = False
        expense.forwarded_to_accountmanager = False
        expense.save()
        messages.warning(request, f"Expense ID {expense.id} has been rejected.")

    else:
        messages.error(request, "Invalid action.")

    return redirect('accountant:expense-approval-dashboard')


@login_required
@permission_required('expenses.can_settle')
def approve_daily_allowance(request, da_id):
    da = get_object_or_404(DailyAllowance, id=da_id)

    if not da.approved:
        da.approved = True
        da.save()
        messages.success(request, f"DA for {da.employee.user.get_full_name()} on {da.date} approved.")
    else:
        messages.info(request, "DA is already approved.")

    return redirect('accountant:expense-approval')


@login_required
@permission_required('expenses.can_settle')
def export_expense_tab_excel(request, tab_name):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_project = request.GET.get('project')

    expenses = Expense.objects.select_related('project', 'employee', 'new_expense_type').all()
    allowances = DailyAllowance.objects.select_related('project', 'employee').all()

    if selected_project and selected_project != "all":
        expenses = expenses.filter(project_id=selected_project)
        allowances = allowances.filter(project_id=selected_project)
    if from_date:
        expenses = expenses.filter(date__gte=from_date)
        allowances = allowances.filter(date__gte=from_date)
    if to_date:
        expenses = expenses.filter(date__lte=to_date)
        allowances = allowances.filter(date__lte=to_date)

    rows = []

    for expense in expenses:
        status = expense.status
        reimbursed = expense.reimbursed
        match = (
            (tab_name == "pending" and status == "Pending") or