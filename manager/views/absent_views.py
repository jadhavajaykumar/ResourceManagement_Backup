from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from datetime import date
from employee.models import EmployeeProfile
from timesheet.models import Attendance



@login_required
@permission_required('timesheet.can_approve')
def mark_absent_dashboard(request):
    if not (request.user.has_perm('timesheet.can_approve') or is_manager(request.user)):

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