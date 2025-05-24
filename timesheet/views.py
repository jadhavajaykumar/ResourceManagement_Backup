from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime
from .models import Timesheet
from .forms import TimesheetForm
from employee.models import EmployeeProfile
from project.models import Project
from expenses.models import DailyAllowance
from timesheet.services.approval_service import approve_or_reject_timesheet
from timesheet.services.export_service import export_timesheets_to_csv
from project.services.da_service import calculate_da

from collections import defaultdict

@login_required
def my_timesheets(request):
    employee = request.user.employeeprofile

    if request.method == 'POST':
        form = TimesheetForm(request.POST, employee=employee)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.employee = employee
            try:
                entry.full_clean()
                entry.save()

                da_amount, currency = calculate_da(entry)
                if da_amount:
                    DailyAllowance.objects.update_or_create(
                        timesheet=entry,
                        defaults={
                            'employee': employee,
                            'project': entry.project,
                            'date': entry.date,
                            'da_amount': da_amount,
                            'currency': currency or 'INR',
                            'forwarded_to_accountant': False,
                            'approved': False,
                            'is_extended': False,
                        }
                    )
                messages.success(request, "Timesheet submitted successfully.")
                return redirect('timesheet:my-timesheets')
            except ValidationError as e:
                form.add_error(None, e.message_dict.get('__all__', ['Invalid submission'])[0])
    else:
        form = TimesheetForm(employee=employee)

    timesheets = Timesheet.objects.filter(employee=employee).order_by('-date', 'time_from')
    weekly_grouped = defaultdict(list)
    for entry in timesheets:
        week_num = entry.date.isocalendar()[1]
        year = entry.date.year
        week_label = f"Week {week_num}, {year}"
        weekly_grouped[week_label].append(entry)

    return render(request, 'timesheet/my_timesheets.html', {
        'form': form,
        'weekly_grouped': dict(weekly_grouped),
    })


@login_required
def approve_timesheet(request, timesheet_id):
    approve_or_reject_timesheet(request, timesheet_id)
    return redirect('timesheet:my-timesheets')

@login_required
def export_timesheets_csv(request):
    employee = request.user.employeeprofile
    timesheets = Timesheet.objects.filter(employee=employee).order_by('-date')
    return export_timesheets_to_csv(timesheets)

@login_required
def edit_timesheet(request, pk):
    employee = request.user.employeeprofile
    timesheet = get_object_or_404(Timesheet, id=pk, employee=employee)

    if timesheet.status == 'Approved':
        messages.error(request, "You cannot edit an approved timesheet.")
        return redirect('timesheet:my-timesheets')

    if request.method == 'POST':
        form = TimesheetForm(request.POST, instance=timesheet, employee=employee)
        if form.is_valid():
            try:
                updated_entry = form.save(commit=False)
                updated_entry.full_clean()
                updated_entry.save()
                messages.success(request, "Timesheet updated.")
                return redirect('timesheet:my-timesheets')
            except ValidationError as e:
                form.add_error(None, e.message_dict.get('__all__', ['Invalid submission'])[0])
    else:
        form = TimesheetForm(instance=timesheet, employee=employee)

    return render(request, 'timesheet/edit_timesheet.html', {
        'form': form,
        'timesheet': timesheet
    })

@login_required
def delete_timesheet(request, timesheet_id):
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)
    if timesheet.is_locked:
        messages.error(request, "Cannot delete a locked timesheet.")
    else:
        timesheet.delete()
        messages.success(request, "Timesheet deleted successfully.")
    return redirect('timesheet:my-timesheets')
