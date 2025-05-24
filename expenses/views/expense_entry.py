from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from collections import defaultdict
from datetime import datetime

from employee.models import EmployeeProfile
from expenses.forms import ExpenseForm
from expenses.models import Expense, ExpenseType, GlobalExpenseSettings, EmployeeExpenseGrace, DailyAllowance, SystemSettings
from project.services.assignment import get_assigned_projects
from timesheet.models import Timesheet

from utils.grace_period import get_allowed_grace_days, is_within_grace


@login_required
def employee_expenses(request):
    user = request.user
    employee = user.employeeprofile
    assigned_projects = get_assigned_projects(employee)

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

    # Filtering logic
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    project_id = request.GET.get('project')
    expense_type_id = request.GET.get('type')

    expenses = Expense.objects.filter(employee=employee, project__in=assigned_projects).select_related('project', 'new_expense_type')
    if start_date and end_date:
        expenses = expenses.filter(date__range=[start_date, end_date])
    if project_id:
        expenses = expenses.filter(project__id=project_id)
    if expense_type_id:
        expenses = expenses.filter(new_expense_type__id=expense_type_id)

    das = DailyAllowance.objects.filter(employee=employee, project__in=assigned_projects)
    if start_date and end_date:
        das = das.filter(date__range=[start_date, end_date])
    if project_id:
        das = das.filter(project__id=project_id)

    grouped_data = defaultdict(lambda: {"expenses": [], "da": None})
    for e in expenses:
        key = (e.project, e.date)
        grouped_data[key]["expenses"].append(e)
    for d in das:
        key = (d.project, d.date)
        grouped_data[key]["da"] = d

    grouped_list = [
        {
            "project": key[0],
            "date": key[1],
            "expenses": value["expenses"],
            "da": value["da"]
        }
        for key, value in grouped_data.items()
    ]

    return render(request, 'expenses/my_expenses.html', {
        'form': form,
        'editing': editing,
        'edit_expense': edit_expense,
        'projects': assigned_projects,
        'expense_types': ExpenseType.objects.all(),
        'grouped_data': grouped_list
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
        'grouped_data': [],
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