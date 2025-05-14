# timesheet/views.py
import csv
import datetime
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import TimesheetForm
from .models import Timesheet
from employee.models import EmployeeProfile
from manager.models import TaskAssignment
from django.contrib import messages

@login_required
def my_timesheets(request):
    employee = request.user.employeeprofile
    

    if request.method == 'POST':
        form = TimesheetForm(request.POST or None, employee=request.user.employeeprofile)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.employee = employee
            entry.full_clean()  # safe now
            entry.save()
            return redirect('timesheet:my-timesheets')
    else:
        form = TimesheetForm()

    timesheets = Timesheet.objects.filter(employee=employee).order_by('-date', 'time_from')

    # Group by date
    grouped = {}
    for entry in timesheets:
        grouped.setdefault(entry.date, []).append(entry)

    return render(request, 'timesheet/my_timesheets.html', {
        'form': form,
        'grouped_timesheets': grouped,
    })


@login_required
def approve_timesheet(request, timesheet_id):
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)
    if request.user.role == 'Manager' and request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Approved', 'Rejected']:
            timesheet.status = status
            timesheet.save()
    return redirect('timesheet:my-timesheets')

@login_required
def export_timesheets_csv(request):
    employee = request.user.employeeprofile
    timesheets = Timesheet.objects.filter(employee=employee).order_by('-date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timesheets.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Project', 'Task', 'Time From', 'Time To', 'Description', 'Status'])

    for entry in timesheets:
        writer.writerow([
            entry.date,
            entry.project.name if entry.project else '',
            entry.task.name if entry.task else '',
            entry.time_from,
            entry.time_to,
            entry.task_description,
            entry.status
        ])
    return response

@login_required
def edit_timesheet(request, pk):
    timesheet = get_object_or_404(Timesheet, id=pk, employee=request.user.employeeprofile)
    if timesheet.status == 'Approved':
        messages.error(request, "You cannot edit an approved timesheet.")
        return redirect('timesheet:my-timesheets')

    if request.method == 'POST':
        form = TimesheetForm(request.POST, instance=timesheet)
        if form.is_valid():
            form.save()
            messages.success(request, "Timesheet updated.")
            return redirect('timesheet:my-timesheets')
    else:
        form = TimesheetForm(instance=timesheet)

    return render(request, 'timesheet/edit_timesheet.html', {'form': form, 'timesheet': timesheet})

# ✅ Correct view signature
def delete_timesheet(request, timesheet_id):
    from .models import Timesheet
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages

    timesheet = get_object_or_404(Timesheet, id=timesheet_id)

    if timesheet.is_locked:
        messages.error(request, "Cannot delete a locked timesheet.")
    else:
        timesheet.delete()
        messages.success(request, "Timesheet deleted successfully.")

    return redirect('timesheet:my-timesheets')  # Adjust if your URL namespace differs
