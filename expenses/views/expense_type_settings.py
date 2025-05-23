# expenses/views/expense_type_settings.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from ..models import ExpenseType
from accounts.access_control import is_manager_or_admin


@login_required
@user_passes_test(is_manager_or_admin)
def edit_expense_type(request, type_id):
    expense_type = get_object_or_404(ExpenseType, id=type_id)

    if request.method == 'POST':
        expense_type.name = request.POST.get('name', expense_type.name)
        expense_type.requires_kilometers = 'requires_kilometers' in request.POST
        expense_type.requires_receipt = 'requires_receipt' in request.POST
        rate = request.POST.get('rate')
        expense_type.rate_per_km = rate if rate else None
        expense_type.save()
        messages.success(request, f"Expense type '{expense_type.name}' updated successfully.")
        return redirect('expenses:expense-settings')

    return render(request, 'expenses/edit_expense_type.html', {'type': expense_type})

@login_required
@user_passes_test(is_manager_or_admin)
def delete_expense_type(request, type_id):
    expense_type = get_object_or_404(ExpenseType, id=type_id)
    expense_type.delete()
    messages.success(request, f"Expense type '{expense_type.name}' deleted successfully.")
    return redirect('expenses:expense-settings')



from ..models import ExpenseType, EmployeeExpenseGrace
from employee.models import EmployeeProfile
from expenses.models import GlobalExpenseSettings

# expenses/views/expense_type_settings.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from ..models import ExpenseType, GlobalExpenseSettings, EmployeeExpenseGrace
from employee.models import EmployeeProfile
from accounts.access_control import is_manager_or_admin

@login_required
@user_passes_test(is_manager_or_admin)
def expense_settings_dashboard(request):
    if request.method == 'POST':
        if 'add_type' in request.POST:
            ExpenseType.objects.create(
                name=request.POST.get('name'),
                requires_kilometers='requires_kilometers' in request.POST,
                requires_receipt='requires_receipt' in request.POST,
                rate_per_km=request.POST.get('rate') or None,
                created_by=request.user
            )
            messages.success(request, "Expense type added.")

        elif 'update_grace' in request.POST:
            days = int(request.POST.get('expense_grace_days'))
            GlobalExpenseSettings.objects.update_or_create(
                id=1,
                defaults={'days': days}
            )
            # Reset all custom grace periods to global value
            EmployeeExpenseGrace.objects.all().update(days=days)
            messages.success(request, f"Global grace period set to {days} days and applied to all employees.")

        elif 'update_employee_grace' in request.POST:
            emp_id = request.POST.get('employee_id')
            days = int(request.POST.get('employee_grace_days'))
            employee = get_object_or_404(EmployeeProfile, id=emp_id)
            EmployeeExpenseGrace.objects.update_or_create(
                employee=employee,
                defaults={'days': days, 'updated_by': request.user}
            )
            messages.success(request, f"Custom grace period of {days} days set for {employee.user.get_full_name()}.")

        elif 'delete_type_id' in request.POST:
            expense_type = get_object_or_404(ExpenseType, id=request.POST.get('delete_type_id'))
            expense_type.delete()
            messages.success(request, f"Deleted expense type {expense_type.name}")

        return redirect('expenses:expense-settings')

    # Query data for display
    types = ExpenseType.objects.all().order_by('name')
    grace_period = GlobalExpenseSettings.objects.first()
    grace_days = grace_period.days if grace_period else 5
    employees = EmployeeProfile.objects.select_related("user").all()
    selected_employee_id = request.GET.get('employee_id')

    selected_employee = None
    employee_grace_period = None
    if selected_employee_id:
        selected_employee = get_object_or_404(EmployeeProfile, id=selected_employee_id)
        grace_obj = EmployeeExpenseGrace.objects.filter(employee=selected_employee).first()
        employee_grace_period = grace_obj.days if grace_obj else grace_days

    # Custom employees with non-default grace
    custom_grace_employees = EmployeeExpenseGrace.objects.exclude(days=grace_days).select_related("employee__user")

    return render(request, 'expenses/expense_settings_dashboard.html', {
        'types': types,
        'grace_period': grace_days,
        'employees': employees,
        'selected_employee': selected_employee,
        'employee_grace_period': employee_grace_period,
        'custom_grace_employees': custom_grace_employees,
    })


