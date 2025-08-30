# manager/views/holiday_views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from timesheet.models import Attendance
from datetime import date

@login_required
@permission_required('timesheet.can_approve')
def manage_holidays(request):
    holidays = Attendance.objects.filter(employee__isnull=True, status='Holiday').order_by('-date')

    if request.method == 'POST':
        if 'add_holiday' in request.POST:
            date_str = request.POST.get('holiday_date')
            description = request.POST.get('holiday_description', '')
            try:
                holiday_date = date.fromisoformat(date_str)
                Attendance.objects.get_or_create(
                    employee=None,
                    date=holiday_date,
                    status='Holiday',
                    defaults={'description': description}
                )
                messages.success(request, f"Holiday added for {holiday_date}")
            except ValueError:
                messages.error(request, "Invalid date format.")

        elif 'delete_holiday' in request.POST:
            holiday_id = request.POST.get('holiday_id')
            Attendance.objects.filter(id=holiday_id, employee=None, status='Holiday').delete()
            messages.success(request, "Holiday deleted.")

        return redirect('manager:manage-holidays')