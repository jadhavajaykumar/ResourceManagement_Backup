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
from expenses.models import (
    Expense, ExpenseType, GlobalExpenseSettings, EmployeeExpenseGrace,
    DailyAllowance, SystemSettings, AdvanceRequest
)
from project.services.assignment import get_assigned_projects
from timesheet.models import Timesheet
from utils.grace_period import get_allowed_grace_days, is_within_grace
from expenses.forms import ExpenseForm, AdvanceRequestForm
# expenses/views/expense_entry.py
from django.http import JsonResponse
from django.template.loader import render_to_string
# expenses/views/expense_entry.py
from project.models import Project  # ✅ add this





@login_required
def employee_expenses(request):
    month_choices = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]
    user = request.user
    employee = user.employeeprofile
    assigned_projects = get_assigned_projects(employee)

    editing = False
    edit_expense = None
    active_tab = request.GET.get('tab', 'new_expense')
    expense_form = ExpenseForm(employee=employee)
    advance_form = AdvanceRequestForm(employee=employee)

    if request.method == 'POST':
        if 'advance_submit' in request.POST:
            active_tab = 'advance'
            advance_form = AdvanceRequestForm(request.POST, employee=employee)
            if advance_form.is_valid():
                advance = advance_form.save(commit=False)
                advance.employee = employee
                advance.save()
                messages.success(request, 'Advance request submitted successfully.')
                return redirect('expenses:employee-expenses')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            expense_id = request.POST.get('expense_id')
            if expense_id:
                expense = get_object_or_404(Expense, id=expense_id, employee=employee)
                expense_form = ExpenseForm(request.POST, request.FILES, instance=expense)
                editing = True
                edit_expense = expense
            else:
                expense_form = ExpenseForm(request.POST, request.FILES, employee=employee)

            if expense_form.is_valid():
                submitted_date = expense_form.cleaned_data.get('date')
                grace_days = get_allowed_grace_days(employee)

                if not is_within_grace(submitted_date, grace_days):
                    messages.error(request, f"Submission not allowed. You can only submit expenses within {grace_days} days.")
                    return redirect('expenses:employee-expenses')

                exp = expense_form.save(commit=False)
                exp.status = 'Submitted'
                exp.employee = employee
                exp.forwarded_to_manager = False
                exp.forwarded_to_accountmanager = False
                exp.save()
                messages.success(request, 'Expense submitted successfully.')
                return redirect('expenses:employee-expenses')
            else:
                messages.error(request, 'Please correct the errors below.')

    # Advance & Deduction Summary
    settled_advances = AdvanceRequest.objects.filter(employee=employee, settled_by_account_manager=True)
    total_advance_amount = settled_advances.aggregate(Sum('amount'))['amount__sum'] or 0
    linked_expenses = Expense.objects.filter(employee=employee, advance_used__in=settled_advances, status='Approved')
    total_deducted = linked_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    current_balance = float(total_advance_amount) - float(total_deducted)
    allow_new_advance = current_balance <= 0
    last_advance = settled_advances.order_by('-settlement_date').first()

    # Expense tabs
    submitted = Expense.objects.filter(employee=employee, status='Submitted')
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

    def stringify(expense):
        return {
            "date": str(expense.date),
            "project": str(expense.project),
            "expense_type": str(expense.new_expense_type.name if expense.new_expense_type else ''),
            "amount": str(expense.amount),
            "status": str(expense.status),
            "from_location": expense.from_location or "",
            "to_location": expense.to_location or ""
        }

    tabbed_expenses = {
        "Submitted": [stringify(e) for e in submitted],
        "Approved": [stringify(e) for e in approved],
        "Settled": [stringify(e) for e in settled],
        "Rejected": [stringify(e) for e in rejected],
        "Daily Allowance": build_list(da, ["date", "project", "da_amount", "approved"]),
        "Advance Requests": build_list(advances, ["date_requested", "purpose", "amount", "settled_by_account_manager"]),
    }

    for tab in tabbed_expenses:
        for row in tabbed_expenses[tab]:
            for key, value in row.items():
                row[key] = str(value)

    return render(request, 'expenses/my_expenses.html', {
        'form': expense_form,
        'advance_form': advance_form,
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
        'active_tab': active_tab,
        'expenses': expenses,
        'month_choices': month_choices,
    })


@login_required
def new_expense_form(request):
    employee = request.user.employeeprofile
    form = ExpenseForm()
    form.fields['project'].queryset = Project.objects.filter(taskassignment__employee=employee).distinct()

    form_html = render_to_string(
        "expenses/expense_form_partial.html",
        {"form": form, "editing": False},
        request=request
    )
    return JsonResponse({"form_html": form_html})


@login_required
def edit_expense_json(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id, employee__user=request.user)

    if expense.status != "Submitted":
        return JsonResponse({"error": "Editing is not allowed for approved/rejected expenses."}, status=403)

    employee = request.user.employeeprofile

    form = ExpenseForm(instance=expense, employee=employee)
    form.fields['project'].queryset = Project.objects.filter(
        taskassignment__employee=employee
    ).distinct()

    # Determine if kilometers should be shown initially
    requires_km = getattr(expense.new_expense_type, "requires_kilometers", False)

    form_html = render_to_string(
        "expenses/expense_form_partial.html",
        {
            "form": form,
            "editing": True,
            "expense": expense,
            "requires_km": requires_km  # Pass to JS/UI
        },
        request=request
    )
    return JsonResponse({"form_html": form_html})
    
@login_required
def delete_advance(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, id=advance_id, employee=request.user.employeeprofile)

    if advance.status == "Submitted" and advance.current_stage == "MANAGER":
        advance.delete()
        messages.success(request, "Advance request deleted successfully.")
    else:
        messages.error(request, "Only submitted advances at Manager stage can be deleted.")

    return redirect('expenses:unified-expense-dashboard')


@login_required
def edit_advance(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, id=advance_id, employee=request.user.employeeprofile)

    if request.method == "POST":
        form = AdvanceRequestForm(request.POST, instance=advance)
        if form.is_valid():
            form.save()
            messages.success(request, "Advance request updated successfully.")
            return redirect('expenses:unified-expense-dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
            return redirect('expenses:unified-expense-dashboard')

    return redirect('expenses:unified-expense-dashboard')


@login_required
def edit_advance_json(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, pk=advance_id, employee__user=request.user)

    # 🔒 Allow edit only if still at MANAGER stage + Submitted
    if not (advance.status == "Submitted" and advance.current_stage == "MANAGER"):
        return JsonResponse({"error": "Editing is allowed only at Manager stage while Submitted."}, status=403)

    form = AdvanceRequestForm(instance=advance, employee=request.user.employeeprofile)
    form_html = render_to_string(
        "expenses/advance_form_partial.html",
        {"form": form, "editing": True, "advance": advance},
        request=request
    )
    return JsonResponse({"form_html": form_html})





    






@login_required
def get_expense_data(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, employee=request.user.employeeprofile)
    form = ExpenseForm(instance=expense)
    
    form_html = render_to_string("expenses/expense_form_partial.html", {
        "form": form,
        "editing": True
    }, request=request)

    return JsonResponse({"success": True, "form_html": form_html})

@login_required
def edit_expense(request, expense_id):
    profile = EmployeeProfile.objects.get(user=request.user)
    expense = get_object_or_404(Expense, id=expense_id, employee=profile)

    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES, instance=expense, employee=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated successfully.")
            return redirect("expenses:unified-expense-dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
            return redirect("expenses:unified-expense-dashboard")
    else:
        form = ExpenseForm(instance=expense, employee=profile)

    return render(request, "expenses/expense_form_partial.html", {
        "form": form,
        "editing": True
    })






@login_required
def delete_expense(request, expense_id):
    profile = EmployeeProfile.objects.get(user=request.user)
    expense = get_object_or_404(Expense, id=expense_id, employee=profile)

    # Allow delete only if still at ACCOUNTANT stage and status is Submitted
    if expense.current_stage == "ACCOUNTANT" and expense.status == "Submitted":
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
    else:
        messages.error(
            request,
            "Only submitted expenses at Accountant stage can be deleted."
        )

    return redirect('expenses:unified-expense-dashboard')



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
