from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from timesheet.models import Timesheet
from employee.models import EmployeeProfile
from project.models import Project
from datetime import datetime
from accounts.access_control import is_manager_or_admin, is_manager
from django.shortcuts import get_object_or_404
from django.contrib import messages



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
    
    
from django.template.loader import render_to_string

def timesheet_approvals(request):
    pending_ts = Timesheet.objects.filter(status='SUBMITTED')  # all pending timesheets
    # If AJAX request (XHR), return a partial HTML (table rows) 
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html_snippet = render_to_string('manager/partials/timesheet_table_rows.html', 
                                        {'timesheets': pending_ts})
        return HttpResponse(html_snippet)
    # Otherwise, render full page
    context = {'timesheets': pending_ts, 'current_page': 'timesheets'}
    return render(request, 'manager/timesheet_approvals.html', context)    


@login_required
@user_passes_test(is_manager)
@require_POST
def handle_timesheet_action(request, timesheet_id, action):
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)

    remark = request.POST.get('manager_remark', '').strip()
    if not remark:
        messages.error(request, "Manager remark is required.")
        return redirect('manager:timesheet-approval')

    if action == 'approve':
        timesheet.status = 'Approved'
        messages.success(request, "Timesheet approved.")
    elif action == 'reject':
        timesheet.status = 'Rejected'
        messages.success(request, "Timesheet rejected.")
    else:
        messages.error(request, "Invalid action.")
        return redirect('manager:timesheet-approval')

    timesheet.manager_remark = remark
    timesheet.save()
    return redirect('manager:timesheet-approval')    
