# expenses/views/expense_entry.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..forms import ExpenseForm
from employee.models import EmployeeProfile
from accounts.access_control import is_manager_or_admin


from django.utils import timezone
from datetime import timedelta


from collections import defaultdict



from ..models import Expense, ExpenseType, DailyAllowance, GlobalExpenseSettings, EmployeeExpenseGrace




@login_required
def employee_expenses(request):
    profile = EmployeeProfile.objects.get(user=request.user)
    expenses = Expense.objects.filter(employee=profile).select_related('project').order_by('-date')
    form = ExpenseForm(request.POST or None, request.FILES or None, employee=profile)

    if request.method == 'POST' and form.is_valid():
        # Grace period logic
        expense_date = form.cleaned_data.get('date')
        grace_days = 0

        grace_obj = EmployeeExpenseGrace.objects.filter(employee=profile).first()
        if grace_obj:
            grace_days = grace_obj.days
        else:
            global_grace = GlobalExpenseSettings.objects.first()
            if global_grace:
                grace_days = global_grace.days

        if expense_date:
            cutoff_date = timezone.now().date() - timedelta(days=grace_days)
            if expense_date < cutoff_date:
                messages.error(request, f"Expenses older than {grace_days} day(s) cannot be submitted.")
            else:
                expense = form.save(commit=False)
                expense.employee = profile
                expense.save()
                messages.success(request, "Expense submitted successfully.")
                return redirect('expenses:employee-expenses')

    # Fetch project list for filter dropdown
    projects = profile.expense_set.select_related('project').values('project__id', 'project__name').distinct()
    expense_types = ExpenseType.objects.all()

    # Fetch Daily Allowance data for each (project, date)
    all_da_entries = DailyAllowance.objects.filter(employee=profile)
    daily_allowances = defaultdict(lambda: {})
    for da in all_da_entries:
        daily_allowances[da.project.id][str(da.date)] = da

    return render(request, 'expenses/my_expenses.html', {
        'form': form,
        'expenses': expenses,
        'expense_types': expense_types,
        'projects': projects,
        'daily_allowances': daily_allowances,  # included for template rendering
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
        'expenses': Expense.objects.filter(employee=profile).order_by('-date'),
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
