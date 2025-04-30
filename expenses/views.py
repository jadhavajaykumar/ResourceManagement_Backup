from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ExpenseForm
from .models import Expense
from employee.models import EmployeeProfile

from django.db.models import Q
from datetime import datetime

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
def employee_expenses(request):
    profile = EmployeeProfile.objects.get(user=request.user)

    # Prefetch project while fetching expenses to avoid N+1 queries
    expenses = Expense.objects.filter(employee=profile).select_related('project').order_by('-date')

    # Filter handling
    if request.method == 'GET':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        project_id = request.GET.get('project')

        if start_date and end_date:
            from django.utils.dateparse import parse_date
            start = parse_date(start_date)
            end = parse_date(end_date)
            if start and end:
                expenses = expenses.filter(date__range=[start, end])

        if project_id:
            expenses = expenses.filter(project_id=project_id)

    # Fetch available projects for dropdown (optimized)
    projects = profile.expense_set.select_related('project').values('project__id', 'project__name').distinct()

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.employee = profile
            expense.save()
            messages.success(request, "Expense submitted successfully.")
            return redirect('expenses:employee-expenses')
    else:
        form = ExpenseForm()

    return render(request, 'expenses/my_expenses.html', {
        'form': form,
        'expenses': expenses,
        'projects': projects,
    })

@login_required
def edit_expense(request, expense_id):
    profile = EmployeeProfile.objects.get(user=request.user)
    expense = get_object_or_404(Expense, id=expense_id, employee=profile)
    
    if expense.status != 'Pending':
        messages.error(request, "Only pending expenses can be edited.")
        return redirect('expenses:employee-expenses')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            updated_expense = form.save(commit=False)
            
            # Recalculate amount if needed
            if updated_expense.expense_type in ['travel-bike', 'travel-personal-car']:
                rate = 5 if updated_expense.expense_type == 'travel-bike' else 12
                updated_expense.amount = updated_expense.kilometers * rate
            
            updated_expense.save()
            messages.success(request, "Expense updated successfully.")
            return redirect('expenses:employee-expenses')
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'expenses/my_expenses.html', {
        'form': form,
        'expenses': Expense.objects.filter(employee=profile).order_by('-date'),
        'editing': True,
        'edit_expense': expense
    })   
    


@login_required
def approve_expense(request, expense_id):
    expense = Expense.objects.get(id=expense_id)
    if request.user.role in ['Manager', 'Accountant']:
        if 'reject' in request.GET:
            expense.status = 'Rejected'
            messages.success(request, f"Expense {expense.id} rejected.")
        else:
            expense.status = 'Approved'
            messages.success(request, f"Expense {expense.id} approved.")
        expense.save()
    return redirect('expenses:employee-expenses')
    

# Update the views.py to handle form save and required validations

