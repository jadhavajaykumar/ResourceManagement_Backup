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
from timesheet.models import Timesheet, TimeSlot, CompOffApplication, CompOffBalance, Attendance, Holiday
from accounts.access_control import is_manager
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
        merged_description = "; ".join(
            slot.description.strip()
            for slot in ts.time_slots.all()
            if slot.description
        )
        ts.merged_description = merged_description

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

        # ✅ Comp-off logic for weekends or holidays
        try:
            timesheet_date = timesheet.date
            is_weekend = timesheet_date.weekday() in [5, 6]  # Saturday or Sunday
            is_holiday = Holiday.objects.filter(date=timesheet_date).exists()

            print(f"🔍 C-OFF Eligibility Check: {timesheet_date} | Weekend={is_weekend}, Holiday={is_holiday}")

            if is_weekend or is_holiday:
                # Debug time slot values
                print("📋 Time Slots Data:", list(timesheet.time_slots.values('date', 'time_from', 'time_to')))

                total_seconds = 0
                for slot in timesheet.time_slots.all():
                    slot_date = slot.date or timesheet.date  # Fallback to timesheet.date
                    if slot.time_from and slot.time_to:
                        try:
                            time_from = datetime.combine(slot_date, slot.time_from)
                            time_to = datetime.combine(slot_date, slot.time_to)
                            total_seconds += (time_to - time_from).total_seconds()
                        except Exception as inner_e:
                            logger.warning(f"⚠️ Error in slot time calculation: {inner_e}")

                hours = total_seconds / 3600
                print(f"🕒 Total Worked Hours on {timesheet_date}: {hours:.2f}")

                if hours >= 4:
                    credited_days = Decimal("1.0")
                elif hours > 0:
                    credited_days = Decimal("0.5")
                else:
                    credited_days = Decimal("0.0")

                print(f"✅ Creditable C-OFF: {credited_days} days")

                if credited_days > 0:
                    balance, created = CompOffBalance.objects.get_or_create(employee=timesheet.employee)
                    before = balance.balance
                    balance.balance += credited_days
                    balance.save()

                    logger.info(
                        f"[C-OFF BALANCE] {timesheet.employee.user.username} | Date={timesheet_date} | "
                        f"Worked Hours={hours:.2f} | Credited={credited_days} | Balance: {before} ➜ {balance.balance}"
                    )
                    print(f"💾 Saved new balance: {before} ➜ {balance.balance}")
                    messages.info(request, f"Comp-off granted: {credited_days} day(s)")
        except Exception as e:
            logger.error(f"❌ Comp-off calculation error for Timesheet {timesheet.id}: {str(e)}", exc_info=True)
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
