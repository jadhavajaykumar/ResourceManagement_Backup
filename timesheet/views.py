# timesheet/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, datetime
from .models import Timesheet
from .forms import TimesheetForm
from employee.models import EmployeeProfile
from project.models import Project
from expenses.models import DailyAllowance, GlobalDASettings

from timesheet.services.approval_service import approve_or_reject_timesheet
from timesheet.services.export_service import export_timesheets_to_csv


@login_required
def my_timesheets(request):
    employee = request.user.employeeprofile

    if request.method == 'POST':
        form = TimesheetForm(request.POST, employee=employee)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.employee = employee
            entry.full_clean()
            entry.save()

            # ----- DA calculation logic -----
            project = entry.project
            

            time_from_dt = datetime.combine(date.today(), entry.time_from)
            time_to_dt = datetime.combine(date.today(), entry.time_to)
            duration_hours = (time_to_dt - time_from_dt).total_seconds() / 3600


            if duration_hours >= 6:
                project = entry.project
                da_config = GlobalDASettings.objects.first()

                if not da_config:
                    da_config = GlobalDASettings.objects.create()

                if project.project_type == 'local':
                    da_amount = da_config.local_da
                elif project.project_type == 'domestic':
                    da_amount = da_config.domestic_da
                elif project.project_type == 'international':
                    da_amount = da_config.international_da
                else:
                    da_amount = 0

                if da_amount > 0:
                    DailyAllowance.objects.update_or_create(
                        timesheet=entry,
                        defaults={
                            'employee': employee,
                            'project': project,
                            'date': entry.date,
                            'da_amount': da_amount,
                            'currency': 'INR',
                            'forwarded_to_accountant': False,
                            'approved': False,
                            'is_extended': False,
                        }
                    )
            # ----- END DA logic -----

            return redirect('timesheet:my-timesheets')
    else:
        form = TimesheetForm(employee=employee)

    timesheets = Timesheet.objects.filter(employee=employee).order_by('-date', 'time_from')
    grouped = {}
    for entry in timesheets:
        grouped.setdefault(entry.date, []).append(entry)

    return render(request, 'timesheet/my_timesheets.html', {
        'form': form,
        'grouped_timesheets': grouped,
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
            form.save()
            messages.success(request, "Timesheet updated.")
            return redirect('timesheet:my-timesheets')
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
