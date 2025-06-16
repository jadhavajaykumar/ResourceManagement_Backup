from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Prefetch
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden
from decimal import Decimal
from datetime import datetime
import logging
from collections import defaultdict
from employee.models import EmployeeProfile
from project.models import Project
from timesheet.models import Timesheet, TimeSlot, CompOffApplication, CompOffBalance, Attendance
from accounts.access_control import is_manager


import logging

from project.services.da_utils import generate_da_for_timesheet  # ✅ DA generation utility


logger = logging.getLogger(__name__)


def get_reportee_queryset(manager):
    return EmployeeProfile.objects.filter(reporting_manager=manager)


@login_required
@user_passes_test(is_manager)
def filtered_timesheet_approvals(request):
    employees = get_reportee_queryset(request.user)
    timesheets = Timesheet.objects.select_related('employee__user')\
        .prefetch_related(Prefetch('time_slots', queryset=TimeSlot.objects.select_related('project', 'task')))\
        .filter(employee__in=employees)

    # Filters
    if (start := request.GET.get('start_date')):
        timesheets = timesheets.filter(date__gte=start)
    if (end := request.GET.get('end_date')):
        timesheets = timesheets.filter(date__lte=end)
    if (proj := request.GET.get('project')):
        timesheets = timesheets.filter(project_id=proj)
    if (emp := request.GET.get('employee')):
        timesheets = timesheets.filter(employee_id=emp)
    if (status := request.GET.get('status')):
        timesheets = timesheets.filter(status=status)

    context = {
        'timesheets': timesheets,
        'projects': Project.objects.all(),
        'employees': employees,
        'current_page': 'timesheet-approvals'
    }
    return render(request, 'manager/timesheet_filtered_dashboard.html', context)





@login_required
@user_passes_test(is_manager)
def timesheet_approval_dashboard(request):
    employees = get_reportee_queryset(request.user)

    timesheets = Timesheet.objects.select_related(
        'employee__user'
    ).prefetch_related(
        Prefetch('time_slots', queryset=TimeSlot.objects.select_related('project', 'task'))
    ).filter(employee__in=employees).order_by('-date', 'shift_start')

    grouped_timesheets = defaultdict(list)
    pending_flags = {}

    for ts in timesheets:
        grouped_timesheets[ts.employee].append(ts)
        if ts.status == 'Pending':
            pending_flags[ts.employee.id] = True

    # ✅ NEW: Load DA records linked to timesheets
    from expenses.models import DailyAllowance
    da_map = {
        da.timesheet_id: da
        for da in DailyAllowance.objects.filter(timesheet__in=timesheets)
    }

    return render(request, 'manager/timesheet_approval_dashboard.html', {
        'grouped_timesheets': dict(grouped_timesheets),
        'pending_flags': pending_flags,
        'da_map': da_map,  # ✅ Pass DA map to template
        'current_page': 'timesheet-approval',
    })






@login_required
@user_passes_test(is_manager)
def timesheet_approvals(request):
    employees = get_reportee_queryset(request.user)
    timesheets = Timesheet.objects.filter(status='SUBMITTED', employee__in=employees)\
        .select_related('employee__user')\
        .prefetch_related(Prefetch('time_slots', queryset=TimeSlot.objects.select_related('project', 'task')))

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html_snippet = render_to_string('manager/partials/timesheet_table_rows.html', {'timesheets': timesheets})
        return HttpResponse(html_snippet)

    context = {'timesheets': timesheets, 'current_page': 'timesheets'}
    return render(request, 'manager/timesheet_approvals.html', context)






@login_required
@user_passes_test(is_manager)
@require_POST
def handle_timesheet_action(request, timesheet_id, action):
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)

    if timesheet.employee.reporting_manager != request.user:
        messages.error(request, "You can only approve/reject timesheets for your direct reports.")
        return redirect('manager:timesheet-approval')

    remark = request.POST.get('manager_remark', '').strip()
    if not remark:
        messages.error(request, "Manager remark is required.")
        return redirect('manager:timesheet-approval')

    if action == 'approve':
        timesheet.status = 'Approved'
        timesheet.manager_remark = remark
        timesheet.save()

        # ✅ Trigger DA generation logic
        print("⏳ Calling generate_da_for_timesheet...")
        try:
            generate_da_for_timesheet(timesheet)
            print("✅ DA generation completed.")
        except Exception as e:
            logger.error(f"DA generation failed for Timesheet ID {timesheet.id}: {str(e)}", exc_info=True)
            messages.warning(request, "Timesheet approved, but DA generation failed.")

        # ✅ Comp-off logic for weekends using related TimeSlot entries
        if timesheet.date.weekday() >= 5:
            try:
                #total_seconds = sum(
                    #(datetime.combine(slot.date, slot.time_to) - datetime.combine(slot.date, slot.time_from)).total_seconds()
                    #for slot in timesheet.time_slots.all()
                #)
                total_seconds = sum(
                    (datetime.combine(slot.date, slot.time_to) - datetime.combine(slot.date, slot.time_from)).total_seconds()
                    for slot in timesheet.time_slots.all()
                    if slot.date and slot.time_from and slot.time_to  # ✅ Ensure all fields are present
)
                hours = total_seconds / 3600
                days_credited = 1.0 if hours >= 4 else 0.5

                balance, _ = CompOffBalance.objects.get_or_create(employee=timesheet.employee)
                credited_days = Decimal(str(credited_days))  # ensure Decimal
                balance.balance += credited_days
                balance.save()
                messages.info(request, f"Comp-off granted: {days_credited} day(s)")
            except Exception as e:
                logger.error(f"Comp-off error: {str(e)}", exc_info=True)
                messages.warning(request, "Approved but comp-off calculation failed.")

    elif action == 'reject':
        timesheet.status = 'Rejected'
        timesheet.manager_remark = remark
        timesheet.save()

    messages.success(request, f"Timesheet {action}d successfully.")
    return redirect('manager:timesheet-approval')



@login_required
@user_passes_test(is_manager)
def approve_c_offs(request):
    pending = CompOffApplication.objects.filter(reviewed=False, employee__reporting_manager=request.user)

    if request.method == 'POST':
        for app_id in request.POST.getlist('approve'):
            app = CompOffApplication.objects.get(id=app_id, employee__reporting_manager=request.user)
            app.approved = True
            app.reviewed = True
            app.save()

            balance = CompOffBalance.objects.get(employee=app.employee)
            balance.balance -= app.days_requested
            balance.save()

        for app_id in request.POST.getlist('reject'):
            app = CompOffApplication.objects.get(id=app_id, employee__reporting_manager=request.user)
            app.approved = False
            app.reviewed = True
            app.save()

        return redirect('manager:approve-c-offs')

    return render(request, 'manager/approve_c_offs.html', {'applications': pending})


@login_required
@user_passes_test(is_manager)
def mark_employee_absent(request):
    if request.method == "POST":
        emp_id = request.POST.get('employee_id')
        date_str = request.POST.get('date')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        employee = get_object_or_404(EmployeeProfile, id=emp_id)
        if employee.reporting_manager != request.user:
            return HttpResponseForbidden("Access denied.")

        Attendance.objects.update_or_create(
            employee=employee,
            date=date_obj,
            defaults={'status': 'Absent', 'added_c_off': 0}
        )

        messages.success(request, f"{employee.user.get_full_name()} marked Absent for {date_obj}")
        return redirect('manager:attendance-dashboard')

    return redirect('manager:attendance-dashboard')


@login_required
@user_passes_test(is_manager)
def timesheet_history_view(request):
    employees = get_reportee_queryset(request.user)
    projects = Project.objects.all()

    timesheets = Timesheet.objects.filter(employee__in=employees)

    if emp_id := request.GET.get('employee'):
        timesheets = timesheets.filter(employee_id=emp_id)
    if project_id := request.GET.get('project'):
        timesheets = timesheets.filter(project_id=project_id)
    if start := request.GET.get('start_date'):
        if end := request.GET.get('end_date'):
            timesheets = timesheets.filter(date__range=[start, end])

    return render(request, 'manager/timesheet_history.html', {
        'employees': employees,
        'projects': projects,
        'timesheets': timesheets,
    })
