
import logging

logger = logging.getLogger(__name__)

from timesheet.utils.slot_utils import generate_time_slots
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import datetime, time, timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from timesheet.services.approval_service import approve_or_reject_timesheet
from timesheet.services.export_service import export_timesheets_to_csv
from project.services.da_service import calculate_da
from calendar import monthrange, monthcalendar
from django.utils.timezone import now
from django.db.models import Prefetch
from collections import defaultdict
from timesheet.utils.calculate_slot_hours import calculate_slot_hours
from django.utils.timezone import localdate
from timesheet.utils.styled_calendar import StyledCalendar
from django.db.models import Min, Max
from django.db import transaction
from timesheet.utils.time_utils import get_current_slot
from ..models import CompOffApplication
from django.db.models import Q

from accounts.access_control import is_manager


from timesheet.utils.calendar_utils import get_timesheet_calendar_data
from timesheet.utils.calculate_attendance import calculate_attendance
from timesheet.utils.get_calendar_entries import get_calendar_entries

from ..services.timesheet_service import process_timesheet_save
import json
import math
from django.forms import modelformset_factory
from datetime import datetime, timedelta, date as date_class, time as time_class
from django.http import JsonResponse  # if not already imported
from ..forms import TimesheetForm, TimeSlotForm

from django.contrib.admin.views.decorators import staff_member_required

from timesheet.models import (
    Timesheet,
    CompensatoryOff,
    CompOffBalance,
    TimeSlot,
    Attendance,
)



@login_required
def load_tasks_for_employee(request):
    
    project_id = request.GET.get("project")
    if not project_id:
        return JsonResponse([], safe=False)

    from skills.models import TaskAssignment
    from project.models import Task

    employee = request.user.employeeprofile
    task_ids = TaskAssignment.objects.filter(
        employee=employee, project_id=project_id
    ).values_list("task_id", flat=True)
    tasks = Task.objects.filter(id__in=task_ids).values("id", "name")
    return JsonResponse(list(tasks), safe=False)





@login_required
def generate_timeslots(request):
    logger.info("Generate timeslots view called")
    if request.method == 'POST':
        form = TimesheetForm(request.POST, employee=request.user.employeeprofile)
        
        if form.is_valid():
            shift_start = form.cleaned_data['shift_start']
            shift_end = form.cleaned_data['shift_end']
            date = form.cleaned_data['date']
            
            time_slots = generate_time_slots(shift_start, shift_end, date)
            total_hours = sum(slot['hours'] for slot in time_slots)
            
            serialized_slots = []
            for slot in time_slots:
                serialized_slots.append({
                    'from_time': slot['from_time'].strftime('%H:%M'),
                    'to_time': slot['to_time'].strftime('%H:%M'),
                    'hours': slot['hours'],
                    'date': date.strftime('%Y-%m-%d')  # ✅ Include date
                })
            
            return JsonResponse({
                'success': True,
                'time_slots': serialized_slots,
                'total_hours': total_hours,
                'slot_count': len(time_slots)
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})




@login_required
def resubmit_timesheet(request, pk):
    employee = request.user.employeeprofile
    timesheet = get_object_or_404(Timesheet, id=pk, employee=employee)

    if timesheet.status != 'Rejected':
        messages.error(request, "Only rejected timesheets can be resubmitted.")
        return redirect('timesheet:my-timesheets')

    TimeSlotFormSet = modelformset_factory(
        TimeSlot,
        form=TimeSlotForm,
        extra=0,
        can_delete=True
    )

    if request.method == 'POST':
        form = TimesheetForm(request.POST, instance=timesheet, employee=employee)
        formset = TimeSlotFormSet(request.POST, queryset=timesheet.time_slots.all(), form_kwargs={'employee': employee})

        if form.is_valid() and formset.is_valid():
            updated_entry = form.save(commit=False)
            updated_entry.status = 'Pending'
            updated_entry.manager_remark = ''
            updated_entry.save()

            time_slots = formset.save(commit=False)
            for slot in time_slots:
                slot.timesheet = updated_entry
                slot.slot_date = updated_entry.date  # ✅ Fixed for C-Off eligibility
                slot.save()

            for deleted_form in formset.deleted_objects:
                deleted_form.delete()

            messages.success(request, "Timesheet resubmitted for approval.")
            return redirect('timesheet:my-timesheets')
        else:
            print("Form or formset invalid")
    else:
        form = TimesheetForm(instance=timesheet, employee=employee)
        formset = TimeSlotFormSet(queryset=timesheet.time_slots.all(), form_kwargs={'employee': employee})

    return render(request, 'timesheet/resubmit_timesheet.html', {
        'form': form,
        'formset': formset,
        'original_entry': timesheet
    })


#Comp off application approval
@login_required
def comp_off_approval_view(request):
    from employee.models import LeaveBalance

    if not (request.user.has_perm('timesheet.can_approve') or is_manager(request.user)):
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    applications = CompOffApplication.objects.select_related('employee__user').all()

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
            leave_balance, _ = LeaveBalance.objects.get_or_create(employee=application.employee)
            if leave_balance.c_off >= application.number_of_days:
                leave_balance.c_off -= application.number_of_days
                leave_balance.save()
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
    # Get all approved timesheets for the employee on that date
    timesheets = Timesheet.objects.filter(
        employee=employee,
        date=date,
        status='Approved',
        time_slots__project=project
    ).distinct()

    # Filter only those timesheets which have slots with the specified project
    timesheets_with_project = timesheets.filter(time_slots__project=project).distinct()

    if timesheets_with_project.count() <= 1:
        return

    with transaction.atomic():
        # Gather all slots from all those timesheets
        all_slots = TimeSlot.objects.filter(timesheet__in=timesheets_with_project, project=project)

        earliest = all_slots.aggregate(Min('time_from'))['time_from__min']
        latest = all_slots.aggregate(Max('time_to'))['time_to__max']
        combined_description = "\n".join(f"• {slot.description.strip()}" for slot in all_slots if slot.description)

        # Keep the first timesheet, delete others
        primary = timesheets_with_project.first()
        timesheets_with_project.exclude(id=primary.id).delete()

        # Update the primary timesheet
        primary.time_from = earliest
        primary.time_to = latest
        primary.task_description = combined_description
        primary.save()


@login_required
def my_timesheets(request):
    from project.models import Project
    
    employee = request.user.employeeprofile

    # ✅ Fix: use working project assignment logic
    assigned_projects = Project.objects.filter(taskassignment__employee=employee).distinct()

    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    day_status_map = get_timesheet_calendar_data(employee, year, month)
    from timesheet.utils.styled_calendar import StyledCalendar
    calendar = StyledCalendar(day_status_map)
    styled_calendar_html = calendar.formatmonth(year, month)

    default_from = datetime.strptime("09:00", "%H:%M").time()
    default_to = datetime.strptime("18:00", "%H:%M").time()

    form = TimesheetForm(
        request.POST or None,
        employee=employee,
        initial={'date': today, 'shift_start': default_from, 'shift_end': default_to}
    )

    show_slots = False
    time_slots = []
    total_hours = 0.0

    if request.method == 'POST':
        if 'slot_count' not in request.POST:
            try:
                shift_start = datetime.strptime(request.POST.get('shift_start'), "%H:%M").time()
                shift_end = datetime.strptime(request.POST.get('shift_end'), "%H:%M").time()
                form.fields['shift_start'].initial = shift_start
                form.fields['shift_end'].initial = shift_end
                show_slots = True
            except Exception:
                pass
        else:
            if form.is_valid():
                timesheet = form.save(commit=False)
                timesheet.employee = employee
                timesheet.save()

                slot_count = int(request.POST.get('slot_count', 0))
                for i in range(1, slot_count + 1):
                    project_id = request.POST.get(f'slot_project_{i}')
                    task_id = request.POST.get(f'slot_task_{i}')
                    from_time = request.POST.get(f'slot_from_{i}')
                    to_time = request.POST.get(f'slot_to_{i}')
                    desc = request.POST.get(f'slot_description_{i}')

                    if not project_id or not from_time or not to_time:
                        continue

                    slot = TimeSlot.objects.create(
                        timesheet=timesheet,
                        employee=employee,
                        project_id=project_id,
                        task_id=task_id,
                        time_from=from_time,
                        time_to=to_time,
                        description=desc,
                        slot_date=timesheet.date
                    )
                    slot.hours = slot.get_duration_hours()
                    slot.save()

                from timesheet.services.timesheetservice import process_timesheet_save
                process_timesheet_save(timesheet)

                return redirect('timesheet:my-timesheets')

    # ✅ Group entries weekly
    timesheet_entries = Timesheet.objects.filter(employee=employee).prefetch_related('time_slots').order_by('-date')
    weekly_grouped = defaultdict(list)
    for entry in timesheet_entries:
        iso_year, iso_week, _ = entry.date.isocalendar()
        label = f"Week {iso_week} ({iso_year})"
        weekly_grouped[label].append(entry)

    context = {
        'form': form,
        'styled_calendar_html': styled_calendar_html,
        'calendar_month': month,
        'calendar_year': year,
        'show_slots': show_slots,
        'assigned_projects': assigned_projects,
        'weekly_grouped': dict(weekly_grouped),
        'employee_id': employee.id,
    }

    return render(request, 'timesheet/my_timesheets.html', context)






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

    TimeSlotFormSet = modelformset_factory(TimeSlot, form=TimeSlotForm, extra=0, can_delete=True)

    if request.method == 'POST':
        form = TimesheetForm(request.POST, instance=timesheet, employee=employee)
        formset = TimeSlotFormSet(request.POST, queryset=timesheet.time_slots.all(),
                                  form_kwargs={'employee': employee})

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    timesheet = form.save(commit=False)
                    if timesheet.status == 'Rejected':
                        timesheet.status = 'Pending'
                    timesheet.full_clean()
                    timesheet.save()

                    time_slots = formset.save(commit=False)
                    for slot in time_slots:
                        slot.timesheet = timesheet
                        slot.employee = employee
                        slot.slot_date = timesheet.date  # ✅ Fixed for C-Off eligibility
                        slot.save()

                    for deleted in formset.deleted_objects:
                        deleted.delete()

                    messages.success(request, "Timesheet and time slots updated successfully.")
                    return redirect('timesheet:my-timesheets')
            except ValidationError as e:
                form.add_error(None, e.message_dict.get('__all__', ['Invalid submission'])[0])
        else:
            print("Form valid:", form.is_valid())
            print("Formset valid:", formset.is_valid())
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
            messages.error(request, "Please correct the errors below.")

    else:
        form = TimesheetForm(instance=timesheet, employee=employee)
        formset = TimeSlotFormSet(queryset=timesheet.time_slots.all(), form_kwargs={'employee': employee})

    return render(request, 'timesheet/edit_timesheet.html', {
        'form': form,
        'formset': formset,
        'timesheet': timesheet
    })


    
@login_required
def delete_timesheet(request, timesheet_id):
    from expenses.models import DailyAllowance
    
    try:
        timesheet = get_object_or_404(
            Timesheet,
            id=timesheet_id,
            employee=request.user.employeeprofile
        )

        if timesheet.status == 'Approved':
            messages.error(request, "Cannot delete an approved timesheet.")
            return redirect('timesheet:my-timesheets')

        if timesheet.is_locked:
            messages.error(request, "Cannot delete a locked timesheet.")
            return redirect('timesheet:my-timesheets')

        with transaction.atomic():
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
    
@login_required
def submit_timesheet(request):
    if request.method == 'POST':
        employee = request.user.employeeprofile
        timesheet_date_str = request.POST.get('date')

        try:
            timesheet_date = datetime.strptime(timesheet_date_str, '%Y-%m-%d').date()

            # ⛔ BLOCK: If employee is marked absent, do not allow submission
            if Attendance.objects.filter(employee=employee, date=timesheet_date, status='Absent').exists():
                messages.error(request, f"You were marked absent on {timesheet_date}. Timesheet submission is not allowed.")
                return redirect('timesheet:my-timesheets')

            with transaction.atomic():
                timesheet = Timesheet.objects.create(
                    employee=employee,
                    date=timesheet_date,
                    shift_start=request.POST.get('shift_start'),
                    shift_end=request.POST.get('shift_end'),
                    is_billable='is_billable' in request.POST
                )

                slot_count = int(request.POST.get('slot_count', 0))
                total_hours = 0.0

                for i in range(1, slot_count + 1):
                    project_id = request.POST.get(f'slot_project_{i}')
                    task_id = request.POST.get(f'slot_task_{i}')
                    description = request.POST.get(f'slot_description_{i}')
                    time_from = request.POST.get(f'slot_from_{i}')
                    time_to = request.POST.get(f'slot_to_{i}')

                    if not all([project_id, time_from, time_to]):
                        continue

                    hours = calculate_slot_hours(time_from, time_to)
                    total_hours += hours

                    date_obj = timesheet_date  # ✅ use this consistently
                    from_dt = datetime.combine(date_obj, datetime.strptime(time_from, '%H:%M').time())
                    to_dt = datetime.combine(date_obj, datetime.strptime(time_to, '%H:%M').time())

                    if to_dt < from_dt:
                        to_dt += timedelta(days=1)

                    slot_date = from_dt.date()

                    TimeSlot.objects.create(
                        timesheet=timesheet,
                        time_from=time_from,
                        time_to=time_to,
                        hours=hours,
                        slot_date=slot_date,            # ✅ Ensure this is set
                        project_id=project_id,
                        task_id=task_id or None,
                        description=description,
                        employee=employee               # ✅ ensure employee set
                    )

                timesheet.total_hours = total_hours
                timesheet.save()

                process_timesheet_save(timesheet)

                messages.success(request, "Timesheet submitted successfully!")
                return redirect('timesheet:my-timesheets')

        except Exception as e:
            logger.error(f"Error saving timesheet: {str(e)}")
            messages.error(request, f"Error saving timesheet: {str(e)}")
            return redirect('timesheet:my-timesheets')

    return redirect('timesheet:my-timesheets')

    
    


@staff_member_required  # only admins
@login_required
def delete_employee_timesheet_data(request, employee_id):
    from employee.models import EmployeeProfile
    from expenses.models import DailyAllowance
    
    manager = request.user
    employee = get_object_or_404(EmployeeProfile, id=employee_id)

    # ✅ Restrict access to only assigned employees
    if not request.user.has_perm('timesheet.can_approve'):
        messages.error(request, "You do not have permission to access this function.")
        return redirect('expenses:expense-settings')  # or any safe fallback page


    # Filter range (GET or POST)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception:
            messages.error(request, "Invalid date range.")
            return redirect(request.path)

        with transaction.atomic():
            Timesheet.objects.filter(employee=employee, date__range=[start_dt, end_dt]).delete()
            DailyAllowance.objects.filter(employee=employee, date__range=[start_dt, end_dt]).delete()
            CompensatoryOff.objects.filter(employee=employee, date_earned__range=[start_dt, end_dt]).delete()
            # Optional: reset balance
            CompOffBalance.objects.filter(employee=employee).update(balance=0)

        messages.success(request, f"Deleted timesheet/DA/C-Off data for {employee.user.get_full_name()} from {start_date} to {end_date}.")
        return redirect('expenses:expense-settings')

    return render(request, 'manager/confirm_delete_employee_data.html', {
        'employee': employee,
        'start_date': start_date,
        'end_date': end_date
    })
    