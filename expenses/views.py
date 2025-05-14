from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ExpenseForm
from .models import Expense
from employee.models import EmployeeProfile

from django.db.models import Q
from datetime import datetime
from .models import SystemSettings
from .forms import GracePeriodForm
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_http_methods
from .models import ExpenseType


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
    new_expense_types = ExpenseType.objects.all()

    # Prefetch project while fetching expenses to avoid N+1 queries
    expenses = Expense.objects.filter(employee=profile).select_related('project').order_by('-date')

    # Filter handling
    if request.method == 'GET':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        project_id = request.GET.get('project')
        expense_type_id = request.GET.get('type')
        if start_date and end_date:
            from django.utils.dateparse import parse_date
            start = parse_date(start_date)
            end = parse_date(end_date)
            if start and end:
                expenses = expenses.filter(date__range=[start, end])

        if project_id:
            expenses = expenses.filter(project_id=project_id)
            
        if expense_type_id:
            expenses = expenses.filter(new_expense_type_id=expense_type_id)

    # Fetch available projects for dropdown (optimized)
    projects = profile.expense_set.select_related('project').values('project__id', 'project__name').distinct()

    if request.method == 'POST':
        form = ExpenseForm(request.POST or None, employee=request.user.employeeprofile)
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
        'expense_types': new_expense_types,
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



def is_manager_or_admin(user):
    return user.is_superuser or (hasattr(user, 'employee_profile') and user.employee_profile.role in ['Manager', 'Admin'])

@login_required
@user_passes_test(is_manager_or_admin)
def manage_expense_settings(request):
    settings_obj, _ = SystemSettings.objects.get_or_create(id=1)

    if request.method == 'POST':
        form = GracePeriodForm(request.POST, instance=settings_obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(request, "Grace period updated successfully.")
            return redirect('expenses:manage-settings')
    else:
        form = GracePeriodForm(instance=settings_obj)

    return render(request, 'expenses/manage_settings.html', {'form': form})




@login_required 
@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'employee_profile') and u.employee_profile.role == 'Manager'))
def expense_settings_dashboard(request):
    system_settings, created = SystemSettings.objects.get_or_create(id=1)
    global_grace_period = system_settings.expense_grace_days

    employees = EmployeeProfile.objects.select_related('user').all()
    selected_employee = None
    employee_grace_period = None

    if request.method == 'POST':
        # Handle Expense Type Form
        if 'add_type' in request.POST:
            name = request.POST.get('name')
            requires_km = 'requires_kilometers' in request.POST
            requires_receipt = 'requires_receipt' in request.POST
            rate = request.POST.get('rate')

            ExpenseType.objects.create(
                name=name,
                requires_kilometers=requires_km,
                requires_receipt=requires_receipt,
                rate_per_km=rate if rate else None,
                created_by=request.user
            )
            messages.success(request, "Expense type added.")
            return redirect('expenses:expense-settings')

        # Handle Global Grace Period
        elif 'update_grace' in request.POST:
            new_days = request.POST.get('expense_grace_days')
            try:
                new_days = int(new_days)
                system_settings.expense_grace_days = new_days
                system_settings.updated_by = request.user
                system_settings.save()
                messages.success(request, "Global grace period updated.")
            except ValueError:
                messages.error(request, "Invalid input for grace period.")
            return redirect('expenses:expense-settings')

        # Handle Per-Employee Grace Period
        elif 'update_employee_grace' in request.POST:
            employee_id = request.POST.get('employee_id')
            new_days = request.POST.get('employee_grace_days')
            try:
                selected_employee = EmployeeProfile.objects.get(id=employee_id)
                new_days = int(new_days)
                selected_employee.grace_period_days = new_days
                selected_employee.save()
                messages.success(request, f"Grace period updated for {selected_employee.user.get_full_name()}")
            except Exception as e:
                messages.error(request, f"Failed to update: {str(e)}")
            return redirect('expenses:expense-settings')

    # Preload grace period for selected employee (optional feature)
    selected_id = request.GET.get('employee_id')
    if selected_id:
        try:
            selected_employee = EmployeeProfile.objects.get(id=selected_id)
            employee_grace_period = selected_employee.grace_period_days
        except:
            selected_employee = None
            employee_grace_period = None

    new_expense_types = ExpenseType.objects.all()
    return render(request, 'expenses/expense_settings_dashboard.html', {
        'types': new_expense_types,
        'grace_period': global_grace_period,
        'employees': employees,
        'selected_employee': selected_employee,
        'employee_grace_period': employee_grace_period,
    })


# expenses/views.py


@login_required
@user_passes_test(is_manager_or_admin)
@require_http_methods(["POST"])
def delete_expense_type(request, type_id):
    new_expense_type = get_object_or_404(ExpenseType, id=type_id)
    new_expense_type.delete()
    messages.success(request, f"Expense type '{new_expense_type.name}' deleted successfully.")
    return redirect('expenses:expense-settings')

@login_required
@user_passes_test(is_manager_or_admin)
def edit_expense_type(request, type_id):
    new_expense_type = get_object_or_404(ExpenseType, id=type_id)

    if request.method == 'POST':
        new_expense_type.name = request.POST.get('name', new_expense_type.name)
        new_expense_type.requires_kilometers = 'requires_kilometers' in request.POST
        new_expense_type.requires_receipt = 'requires_receipt' in request.POST
        rate = request.POST.get('rate')
        new_expense_type.rate_per_km = rate if rate else None
        new_expense_type.save()

        messages.success(request, f"Expense type '{new_expense_type.name}' updated successfully.")
        return redirect('expenses:expense-settings')

    return render(request, 'expenses/edit_expense_type.html', {
        'type': new_expense_type
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import CountryDASettingForm
from .models import CountryDARate

# ✅ Access control: Only managers and admins
def is_manager_or_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name__in=['Manager', 'Admin']).exists())

# ✅ Manage all Country DA Rates (Add or View)
@login_required
@user_passes_test(is_manager_or_admin)
def manage_country_da(request):
    form = CountryDASettingForm()
    country_rates = CountryDARate.objects.all().order_by('country')

    if request.method == "POST" and 'add_country' in request.POST:
        form = CountryDASettingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Country DA settings added successfully.")
            return redirect('expenses:manage-country-da')

    return render(request, 'expenses/manage_country_da.html', {
        'form': form,
        'country_rates': country_rates,
        'edit_mode': False,
    })

# ✅ Edit Country DA Rate
@login_required
@user_passes_test(is_manager_or_admin)
def edit_country_da(request, rate_id):
    instance = get_object_or_404(CountryDARate, id=rate_id)
    form = CountryDASettingForm(request.POST or None, instance=instance)
    country_rates = CountryDARate.objects.all().order_by('country')

    if request.method == "POST" and 'update_country' in request.POST:
        if form.is_valid():
            form.save()
            messages.success(request, "Country DA settings updated.")
            return redirect('expenses:manage-country-da')

    return render(request, 'expenses/manage_country_da.html', {
        'form': form,
        'country_rates': country_rates,
        'edit_mode': True,
    })

# ✅ Delete Country DA Rate
@login_required
@user_passes_test(is_manager_or_admin)
def delete_country_da(request, rate_id):
    if request.method == "POST":
        rate = get_object_or_404(CountryDARate, id=rate_id)
        rate.delete()
        messages.success(request, f"{rate.country} removed successfully.")
    return redirect('expenses:manage-country-da')
