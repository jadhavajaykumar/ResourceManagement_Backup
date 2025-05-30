# timesheet/services/approval_service.py

from django.shortcuts import get_object_or_404
from timesheet.models import Timesheet
from django.contrib import messages

# approval_service.py



from timesheet.services.timesheet_merge_service import merge_all_for_employee_date

def approve_or_reject_timesheet(request, timesheet_id):
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)

    if request.user.role != 'Manager':
        messages.error(request, "Only managers can approve or reject timesheets.")
        return

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Approved', 'Rejected']:
            timesheet.status = status
            timesheet.save()

            if status == 'Approved':
                # ✅ Run merge for all approved entries for this date + employee
                merge_all_for_employee_date(
                    employee=timesheet.employee,
                    date=timesheet.date
                )

            messages.success(request, f"Timesheet {status.lower()} successfully.")
        else:
            messages.error(request, "Invalid status provided.")
