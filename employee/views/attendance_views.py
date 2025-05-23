# employee/views/attendance_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from timesheet.models import Attendance

@login_required
def attendance_report(request):
    profile = request.user.employeeprofile
    records = Attendance.objects.filter(employee=profile).order_by('-date')
    return render(request, 'employee/attendance_report.html', {'records': records})
