from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import date
from employee.models import EmployeeProfile
from timesheet.models import Attendance
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.access_control import is_manager_or_admin, is_manager
@user_passes_test(is_manager)
@login_required
def mark_absent_dashboard(request):
    if not request.user.is_manager:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    employees = EmployeeProfile.objects.all()
    context = {'employees': employees}

    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        date_str = request.POST.get('absent_date')
        try:
            absent_date = date.fromisoformat(date_str)
        except ValueError:
            messages.error(request, "Invalid date.")
            return redirect('manager:mark-absent-dashboard')

        employee = Employee.objects.get(id=emp_id)
        Attendance.objects.get_or_create(employee=employee, date=absent_date, status='Absent')
        messages.success(request, f"{employee.user.get_full_name()} marked absent on {absent_date}")
        return redirect('manager:mark-absent-dashboard')

    return render(request, 'manager/mark_absent_dashboard.html', context)
