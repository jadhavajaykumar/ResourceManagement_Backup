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
from timesheet.utils.styled_calendar import StyledCalendar
from django.db.models import Min, Max
from django.db import transaction
from timesheet.utils.time_utils import get_current_slot
from .models import CompOffApplication
from django.db.models import Q
from timesheet.models import Attendance  # Ensure this import exists
from employee.models import LeaveBalance  # ✅ ensure this is imported
from timesheet.utils.calendar_utils import get_timesheet_calendar_data  # You already use this








@login_required 
def comp_off_approval_view(request):
    if not request.user.is_manager:
        messages.error(request, "Access denied.")
        return redirect('dashboard')  # Adjust to your actual dashboard URL

    applications = CompOffApplication.objects.select_related('employee__user').all()

    # Filters
    name = request.GET.get('employee')
    status = request.GET.get('status')
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    if name:
        applications = applications.filter(employee__user__first_name__icontains=name)

    if status:
        applications = applications.filter(status=status)

    if start and end:
        applications = applications.filter(date_applied_for__range=[start, end])

    if request.method == 'POST':
        app_id = request.POST.get('app_id')
        action = request.POST.get('action')
        application = get_object_or_404(CompOffApplication, id=app_id)

        if action == 'approve':
            # Get or create leave balance
            leave_balance, _ = LeaveBalance.objects.get_or_create(employee=application.employee)

            if leave_balance.c_off >= application.number_of_days:
                # Deduct from balance
                leave_balance.c_off -= application.number_of_days
                leave_balance.save()

                # Approve application
                application.status = 'Approved'
                application.save()

                messages.success(request, f"Approved application for {application.employee}")
            else:
                messages.error(request, "Insufficient C-Off balance to approve request.")
                return redirect('timesheet:comp-off-approvals')

        elif action == 'reject':
            application.status = 'Rejected'
            application.save()
            messages.info(request, f"Rejected application for {application.employee}")

        return redirect('timesheet:comp-off-approvals')

    return render(request, 'timesheet/comp_off_approval.html', {
        'applications': applications,
    })




def merge_timesheets_for_employee(employee, project, date):
    entries = Timesheet.objects.filter(
        employee=employee,
        project=project,
        date=date,
        status='Approved'
    )

    if entries.count() <= 1:
        return  # Nothing to merge

    with transaction.atomic():
        earliest = entries.aggregate(Min('time_from'))['time_from__min']
        latest = entries.aggregate(Max('time_to'))['time_to__max']
        combined_description = "\n".join(f"• {entry.task_description.strip()}" for entry in entries)

        # Keep the first entry, delete others
        primary = entries.first()
        entries.exclude(id=primary.id).delete()

        primary.time_from = earliest
        primary.time_to = latest
        primary.task_description = combined_description
        primary.save()

#from .utils import get_current_slot, get_timesheet_calendar_data














@login_required
def my_timesheets(request):
    employee = request.user.employeeprofile
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # Get detailed day status map
    day_status_map = get_timesheet_calendar_data(employee, year, month)

    # Generate styled calendar
    calendar = StyledCalendar(day_status_map)
    styled_calendar_html = calendar.formatmonth(year, month)

    # Default timeslot
    default_from, default_to = get_current_slot()

    if request.method == 'POST':
        form = TimesheetForm(request.POST, employee=employee)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.employee = employee

            # Additional server-side future date check
            if entry.date > today:
                form.add_error('date', "Cannot submit timesheets for future dates")
            elif Attendance.objects.filter(employee=employee, date=entry.date, status='Absent').exists():
                form.add_error(None, f"You were marked absent on {entry.date}. Timesheet cannot be submitted.")
            else:
                if entry.is_billable is None:
                    entry.is_billable = False

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
        form = TimesheetForm(
            employee=employee,
            initial={
                'date': today,
                'time_from': default_from,
                'time_to': default_to,
            }
        )

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
        'styled_calendar_html': styled_calendar_html,
        'calendar_year': year,
        'calendar_month': month,
    })

# ... [Keep all other existing view functions unchanged] ...





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
    """
    Handles deletion of timesheet entries with proper validation and error handling
    Args:
        request: HttpRequest object
        timesheet_id: ID of the timesheet to delete
    Returns:
        Redirect to my-timesheets view with appropriate message
    """
    try:
        # Get the timesheet or return 404
        timesheet = get_object_or_404(
            Timesheet,
            id=timesheet_id,
            employee=request.user.employeeprofile  # Ensure user owns the timesheet
        )

        # Check if timesheet is approved
        if timesheet.status == 'Approved':
            messages.error(request, "Cannot delete an approved timesheet.")
            return redirect('timesheet:my-timesheets')

        # Check if timesheet is locked
        if timesheet.is_locked:
            messages.error(request, "Cannot delete a locked timesheet.")
            return redirect('timesheet:my-timesheets')

        # Check if timesheet is pending approval
        if timesheet.status == 'Pending':
            # Optional: Add notification to manager about cancellation
            pass

        # All checks passed - delete the timesheet
        with transaction.atomic():
            # Delete any related records first if needed
            DailyAllowance.objects.filter(timesheet=timesheet).delete()
            timesheet.delete()
            
        messages.success(request, "Timesheet deleted successfully.")
        
    except PermissionDenied:
        messages.error(request, "You don't have permission to delete this timesheet.")
    except Exception as e:
        logger.error(f"Error deleting timesheet {timesheet_id}: {str(e)}")
        messages.error(request, "An error occurred while deleting the timesheet.")

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


