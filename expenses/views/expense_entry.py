from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from collections import defaultdict
from datetime import datetime
from django.db.models import Sum
import io
import xlsxwriter

from employee.models import EmployeeProfile
from expenses.forms import ExpenseForm
from expenses.models import (
    Expense, ExpenseType, GlobalExpenseSettings, EmployeeExpenseGrace,
    DailyAllowance, SystemSettings, AdvanceRequest
)
from project.services.assignment import get_assigned_projects
from timesheet.models import Timesheet
from utils.grace_period import get_allowed_grace_days, is_within_grace

@login_required
def employee_expenses(request):
    user = request.user
    employee = user.employeeprofile
    assigned_projects = get_assigned_projects(employee)

    # Form logic
    editing = False
    edit_expense = None

    if request.method == 'POST':
        if 'expense_id' in request.POST:
            expense = get_object_or_404(Expense, id=request.POST['expense_id'], employee=employee)
            form = ExpenseForm(request.POST, request.FILES, instance=expense)
            editing = True
            edit_expense = expense
        else:
            form = ExpenseForm(request.POST, request.FILES, employee=employee)

        if form.is_valid():
            submitted_date = form.cleaned_data.get('date')
            grace_days = get_allowed_grace_days(employee)

            if not is_within_grace(submitted_date, grace_days):
                messages.error(
                    request,
                    f"Submission not allowed. You can only submit expenses within {grace_days} days."
                )
                return redirect('expenses:employee-expenses')

            exp = form.save(commit=False)
            exp.employee = employee
            exp.save()
            messages.success(request, 'Expense submitted successfully.')
            return redirect('expenses:employee-expenses')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ExpenseForm(employee=employee)

    # Advance tracking
    settled_advances = AdvanceRequest.objects.filter(employee=employee, settled_by_account_manager=True)
    total_advance_amount = settled_advances.aggregate(Sum('amount'))['amount__sum'] or 0
    linked_expenses = Expense.objects.filter(employee=employee, advance_used__in=settled_advances, status='Approved')
    total_deducted = linked_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    current_balance = float(total_advance_amount) - float(total_deducted)
    allow_new_advance = current_balance <= 0
    last_advance = settled_advances.order_by('-settlement_date').first()

    # Tab data
    submitted = Expense.objects.filter(employee=employee, status='Pending')
    approved = Expense.objects.filter(employee=employee, status='Approved', reimbursed=False)
    settled = Expense.objects.filter(employee=employee, status='Approved', reimbursed=True)
    rejected = Expense.objects.filter(employee=employee, status='Rejected')
    da = DailyAllowance.objects.filter(employee=employee)
    advances = AdvanceRequest.objects.filter(employee=employee)

    def build_list(queryset, fields):
        return [
            {field: getattr(obj, field) for field in fields}
            for obj in queryset
        ]

    tabbed_expenses = {
        "Submitted": build_list(submitted, ["date", "project", "new_expense_type", "amount", "status"]),
        "Approved": build_list(approved, ["date", "project", "new_expense_type", "amount", "status"]),
        "Settled": build_list(settled, ["date", "project", "new_expense_type", "amount", "status"]),
        "Rejected": build_list(rejected, ["date", "project", "new_expense_type", "amount", "status"]),
        "Daily Allowance": build_list(da, ["date", "project", "da_amount", "approved"]),
        "Advance Requests": build_list(advances, ["date_requested", "purpose", "amount", "settled_by_account_manager"]),
    }

    for tab in tabbed_expenses:
        for row in tabbed_expenses[tab]:
            for key, value in row.items():
                row[key] = str(value)  # Ensure display-safe values

    return render(request, 'expenses/my_expenses.html', {
        'form': form,
        'editing': editing,
        'edit_expense': edit_expense,
        'projects': assigned_projects,
        'expense_types': ExpenseType.objects.all(),
        'tabbed_expenses': tabbed_expenses,
        'latest_advance': last_advance,
        'current_balance': current_balance,
        'allow_new_advance': allow_new_advance,
        
        'submitted_expenses': submitted,
        'approved_expenses': approved,
        'settled_expenses': settled,
        'rejected_expenses': rejected,
        'da_entries': da,
        'advance_entries': advances,
        

    })


@login_required
def edit_expense(request, expense_id):
    profile = EmployeeProfile.objects.get(user=request.user)
    expense = get_object_or_404(Expense, id=expense_id, employee=profile)

    if expense.status != 'Pending':
        messages.error(request, "Only pending expenses can be edited.")
        return redirect('expenses:employee-expenses')

    form = ExpenseForm(request.POST or None, request.FILES or None, instance=expense, employee=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Expense updated successfully.")
        return redirect('expenses:employee-expenses')

    return render(request, 'expenses/my_expenses.html', {
        'form': form,
        'expense_types': ExpenseType.objects.all(),
        'projects': get_assigned_projects(profile),
        'tabbed_expenses': {},
        'editing': True,
        'edit_expense': expense
    })


@login_required
def delete_expense(request, expense_id):
    profile = EmployeeProfile.objects.get(user=request.user)
    expense = get_object_or_404(Expense, id=expense_id, employee=profile)

    if expense.status == 'Pending':
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
    else:
        messages.error(request, "Only pending expenses can be deleted.")

    return redirect('expenses:employee-expenses')


@login_required
def export_expense_tab(request, tab_name):
    employee = request.user.employeeprofile

    tabs = {
        "Submitted": Expense.objects.filter(employee=employee, status='Pending'),
        "Approved": Expense.objects.filter(employee=employee, status='Approved', reimbursed=False),
        "Settled": Expense.objects.filter(employee=employee, status='Approved', reimbursed=True),
        "Rejected": Expense.objects.filter(employee=employee, status='Rejected'),
        "Daily Allowance": DailyAllowance.objects.filter(employee=employee),
        "Advance Requests": AdvanceRequest.objects.filter(employee=employee),
    }

    data = tabs.get(tab_name)
    if not data:
        return HttpResponse("Invalid tab name", status=400)

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet(tab_name)

    if tab_name in ["Submitted", "Approved", "Settled", "Rejected"]:
        headers = ["Date", "Project", "Type", "Amount", "Status"]
        rows = [
            [str(exp.date), str(exp.project), str(exp.new_expense_type), float(exp.amount), exp.status]
            for exp in data
        ]
    elif tab_name == "Daily Allowance":
        headers = ["Date", "Project", "DA Amount", "Approved"]
        rows = [
            [str(da.date), str(da.project), float(da.da_amount), da.approved]
            for da in data
        ]
    elif tab_name == "Advance Requests":
        headers = ["Date Requested", "Purpose", "Amount", "Settled"]
        rows = [
            [str(adv.date_requested), adv.purpose, float(adv.amount), adv.settled_by_account_manager]
            for adv in data
        ]

    for col, header in enumerate(headers):
        sheet.write(0, col, header)

    for row_idx, row in enumerate(rows, 1):
        for col_idx, cell in enumerate(row):
            sheet.write(row_idx, col_idx, cell)

    workbook.close()
    output.seek(0)

    filename = f"{tab_name}_export.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response
