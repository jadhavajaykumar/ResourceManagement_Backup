from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, time, timedelta, date
from .models import Timesheet
from .forms import TimesheetForm
from employee.models import EmployeeProfile
from project.models import Project
from expenses.models import DailyAllowance
from timesheet.services.approval_service import approve_or_reject_timesheet
from timesheet.services.export_service import export_timesheets_to_csv
from project.services.da_service import calculate_da
from calendar import monthrange, monthcalendar
from django.utils.timezone import now

from collections import defaultdict
from calendar import monthrange

from django.utils.timezone import localdate


def merge_timesheet_entries(entries):
    grouped = defaultdict(lambda: {'start': None, 'end': None, 'tasks': []})

    for entry in entries:
        key = (entry.date, entry.project.project_name)
        start = datetime.strptime(entry.start_time.strftime('%H:%M'), '%H:%M')
        end = datetime.strptime(entry.end_time.strftime('%H:%M'), '%H:%M')

        if grouped[key]['start'] is None or start < grouped[key]['start']:
            grouped[key]['start'] = start
        if grouped[key]['end'] is None or end > grouped[key]['end']:
            grouped[key]['end'] = end
        grouped[key]['tasks'].append(entry.task_description)

    merged = []
    for (date, project), values in grouped.items():
        merged.append({
            'date': date,
            'project': project,
            'start_time': values['start'].strftime('%H:%M'),
            'end_time': values['end'].strftime('%H:%M'),
            'tasks': values['tasks'],
        })

    return merged


#from .utils import get_current_slot, get_timesheet_calendar_data


def get_timesheet_calendar_data(employee, year, month):
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    entries = Timesheet.objects.filter(
        employee=employee,
        date__range=(start_date, end_date)
    )

    day_data = defaultdict(lambda: {
        'status': 'no_entry', 'hours': 0, 'approved': False, 'is_weekend': False
    })

    for entry in entries:
        key = entry.date
        start = datetime.combine(entry.date, entry.time_from)
        end = datetime.combine(entry.date, entry.time_to)
        duration = (end - start).total_seconds() / 3600

        if day_data[key]['hours'] < duration:
            day_data[key]['hours'] = duration
            day_data[key]['status'] = 'approved' if entry.status == 'Approved' else 'submitted'
            day_data[key]['approved'] = entry.status == 'Approved'

    for day in range(1, end_date.day + 1):
        dt = date(year, month, day)
        if dt not in day_data:
            day_data[dt]['status'] = 'no_entry'
        elif day_data[dt]['hours'] < 9 and day_data[dt]['status'] != 'no_entry':
            day_data[dt]['status'] = 'incomplete'
        if dt.weekday() >= 5 and day_data[dt]['approved']:  # Saturday or Sunday
            day_data[dt]['status'] = 'c_off'

        day_data[dt]['is_weekend'] = dt.weekday() >= 5

    return day_data


# Time slot definitions (you may move this to utils.py if preferred)
TIME_SLOTS = [
    (time(9, 0), time(11, 0)),
    (time(11, 0), time(13, 0)),
    (time(13, 0), time(13, 30)),  # lunch
    (time(13, 30), time(15, 30)),
    (time(15, 30), time(17, 30)),
    (time(17, 30), time(18, 15)),
]

def get_current_slot():
    now = datetime.now().time()
    for start, end in TIME_SLOTS:
        if start <= now <= end:
            return start, end
    return time(9, 0), time(11, 0)  # default fallback




@login_required
def my_timesheets(request):
    employee = request.user.employeeprofile
    today = timezone.now().date()
    year, month = today.year, today.month

    # Get timesheet entries for current month
    calendar_entries = Timesheet.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month
    ).values('date', 'status', 'time_from', 'time_to')

    # Build map of date => total hours and status
    day_status_map = {}
    for entry in calendar_entries:
        date = entry['date']
        duration = (datetime.combine(date, entry['time_to']) - datetime.combine(date, entry['time_from'])).total_seconds() / 3600
        if date not in day_status_map:
            day_status_map[date] = {'total_hours': duration, 'status': entry['status']}
        else:
            day_status_map[date]['total_hours'] += duration
            if day_status_map[date]['total_hours'] > 9:
                day_status_map[date]['total_hours'] = 9

    # Build the calendar matrix for the current month
    month_matrix = monthcalendar(year, month)
    calendar_weeks = []
    for week in month_matrix:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append((None, 'empty'))
            else:
                date_obj = datetime(year, month, day).date()
                if date_obj not in day_status_map:
                    status = 'not_submitted'
                else:
                    entry = day_status_map[date_obj]
                    if entry['total_hours'] >= 9:
                        status = 'approved' if entry['status'] == 'Approved' else 'submitted'
                    else:
                        status = 'partial'
                week_row.append((date_obj, status))
        calendar_weeks.append(week_row)

    # Timesheet form with default time slot
    default_from, default_to = get_current_slot()

    if request.method == 'POST':
        form = TimesheetForm(request.POST, employee=employee)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.employee = employee

            # Ensure is_billable is not null
            if entry.is_billable is None:
                entry.is_billable = False  # Or apply logic as needed

            try:
                entry.full_clean()
                entry.save()

                # DA calculation
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
        form = TimesheetForm(
            employee=employee,
            initial={
                'date': today,
                'time_from': default_from,
                'time_to': default_to,
            }
        )

    # Weekly grouping of submitted timesheets
    timesheets = Timesheet.objects.filter(employee=employee).order_by('-date', 'time_from')
    weekly_grouped = defaultdict(list)
    for entry in timesheets:
        week_num = entry.date.isocalendar()[1]
        week_year = entry.date.year
        label = f"Week {week_num}, {week_year}"
        weekly_grouped[label].append(entry)

    return render(request, 'timesheet/my_timesheets.html', {
        'form': form,
        'weekly_grouped': dict(weekly_grouped),
        'calendar_weeks': calendar_weeks,
        'calendar_year': year,
        'calendar_month': month,
        'days_of_week': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
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


@login_required
def apply_c_off(request):
    employee = request.user.employeeprofile
    balance = CompOffBalance.objects.filter(employee=employee).first()

    if request.method == 'POST':
        form = CompOffApplicationForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.employee = employee
            if obj.days_requested <= balance.balance:
                obj.save()
                messages.success(request, "C-Off application submitted.")
                return redirect('timesheet:my-c-offs')
            else:
                form.add_error('days_requested', "Insufficient balance.")
    else:
        form = CompOffApplicationForm()

    return render(request, 'timesheet/apply_c_off.html', {'form': form, 'balance': balance})


