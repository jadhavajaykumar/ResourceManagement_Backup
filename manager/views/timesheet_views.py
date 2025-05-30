from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import HttpResponse
from decimal import Decimal
from timesheet.models import Timesheet
from employee.models import EmployeeProfile
from project.models import Project
from accounts.access_control import is_manager_or_admin, is_manager

# Import C-off models
from timesheet.models import CompOffApplication, CompOffBalance

from datetime import datetime, timedelta
from timesheet.models import Timesheet
from django.db.models import Q



from timesheet.models import Attendance

from django.http import HttpResponseForbidden

@login_required
@user_passes_test(is_manager)
def filtered_timesheet_approvals(request):
    timesheets = Timesheet.objects.select_related('employee__user', 'project', 'task').all()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    project_id = request.GET.get('project')
    employee_id = request.GET.get('employee')
    status = request.GET.get('status')

    if start_date:
        timesheets = timesheets.filter(date__gte=start_date)
    if end_date:
        timesheets = timesheets.filter(date__lte=end_date)
    if project_id:
        timesheets = timesheets.filter(project_id=project_id)
    if employee_id:
        timesheets = timesheets.filter(employee_id=employee_id)
    if status:
        timesheets = timesheets.filter(status=status)

    context = {
        'timesheets': timesheets,
        'projects': Project.objects.all(),
        'employees': EmployeeProfile.objects.all(),
        'current_page': 'timesheet-approvals'
    }
    return render(request, 'manager/timesheet_filtered_dashboard.html', context)


@login_required
@user_passes_test(is_manager)
def timesheet_approval_dashboard(request):
    timesheets = Timesheet.objects.select_related('employee__user', 'project', 'task') \
                                  .filter(status='Pending') \
                                  .order_by('-date', 'time_from')
    return render(request, 'manager/timesheet_approval_dashboard.html', {'timesheets': timesheets})


def timesheet_approvals(request):
    pending_ts = Timesheet.objects.filter(status='SUBMITTED')  # all pending timesheets
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html_snippet = render_to_string('manager/partials/timesheet_table_rows.html', {'timesheets': pending_ts})
        return HttpResponse(html_snippet)
    context = {'timesheets': pending_ts, 'current_page': 'timesheets'}
    return render(request, 'manager/timesheet_approvals.html', context)


@login_required
@user_passes_test(is_manager)
@require_POST
def handle_timesheet_action(request, timesheet_id, action):
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)
    remark = request.POST.get('Manager_Remark', '').strip()

    if not remark:
        messages.error(request, "Manager Remark is required.")
        return redirect('manager:timesheet-approval')

    if action == 'approve':
        timesheet.status = 'Approved'
        timesheet.manager_remark = remark
        timesheet.save()

        # Auto-grant C-off if applicable (for Sat/Sun)
        if timesheet.date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            time_delta = datetime.combine(timesheet.date, timesheet.time_to) - datetime.combine(timesheet.date, timesheet.time_from)
            hours = time_delta.total_seconds() / 3600

            days_credited = 1.0 if hours >= 4 else 0.5

            balance, _ = CompOffBalance.objects.get_or_create(employee=timesheet.employee)
          

            balance.balance += Decimal(str(days_credited))

            balance.save()

        messages.success(request, "Timesheet approved.")
    elif action == 'reject':
        timesheet.status = 'Rejected'
        timesheet.manager_remark = remark
        timesheet.save()
        messages.success(request, "Timesheet rejected.")
    else:
        messages.error(request, "Invalid action.")

    return redirect('manager:timesheet-approval')


@login_required
@user_passes_test(is_manager)
def approve_c_offs(request):
    pending = CompOffApplication.objects.filter(reviewed=False)
    if request.method == 'POST':
        for app_id in request.POST.getlist('approve'):
            app = CompOffApplication.objects.get(id=app_id)
            app.approved = True
            app.reviewed = True
            app.save()

            balance = CompOffBalance.objects.get(employee=app.employee)
            balance.balance -= app.days_requested
            balance.save()

        for app_id in request.POST.getlist('reject'):
            app = CompOffApplication.objects.get(id=app_id)
            app.approved = False
            app.reviewed = True
            app.save()

        return redirect('manager:approve-c-offs')

    return render(request, 'manager/approve_c_offs.html', {'applications': pending})



@login_required
def mark_employee_absent(request):
    if not request.user.is_manager:
        return HttpResponseForbidden()

    if request.method == "POST":
        emp_id = request.POST.get('employee_id')
        date_str = request.POST.get('date')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        employee = get_object_or_404(EmployeeProfile, id=emp_id)

        Attendance.objects.update_or_create(
            employee=employee,
            date=date_obj,
            defaults={'status': 'Absent', 'added_c_off': 0}
        )

        messages.success(request, f"{employee.user.get_full_name()} marked Absent for {date_obj}")
        return redirect('manager:attendance-dashboard')  # Adjust as needed

    return redirect('manager:attendance-dashboard')



@login_required
def timesheet_history_view(request):
    if not request.user.is_manager:
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    employees = Employee.objects.all()
    projects = Project.objects.all()

    emp_id = request.GET.get('employee')
    project_id = request.GET.get('project')
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    timesheets = Timesheet.objects.all()

    if emp_id:
        timesheets = timesheets.filter(employee_id=emp_id)
    if project_id:
        timesheets = timesheets.filter(project_id=project_id)
    if start and end:
        timesheets = timesheets.filter(date__range=[start, end])

    context = {
        'employees': employees,
        'projects': projects,
        'timesheets': timesheets,
    }

    return render(request, 'manager/timesheet_history.html', context)
