# utils/dev_tools.py or a temporary admin view

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from expenses.models import AdvanceRequest, Expense, DailyAllowance
from employee.models import EmployeeProfile

def delete_employee_financial_data(request, employee_id):
    employee = get_object_or_404(EmployeeProfile, id=employee_id)

    # Delete expenses
    Expense.objects.filter(employee=employee).delete()

    # Delete DA if relevant
    DailyAllowance.objects.filter(employee=employee).delete()

    # Delete advances
    AdvanceRequest.objects.filter(employee=employee).delete()

    messages.success(request, f"All expense, DA, and advance data deleted for {employee.user.get_full_name()}")
    return redirect('admin_dashboard_or_test_url')
