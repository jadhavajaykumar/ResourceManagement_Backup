# employee/views/attendance_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from timesheet.models import Attendance
from datetime import datetime, timedelta, date
from calendar import monthrange
from django.utils.timezone import now
from timesheet.models import Timesheet, CompOffBalance, CompOffApplication
from employee.forms import CompOffApplicationForm

#from employee.forms import CompOffApplicationForm

@login_required
def attendance_report(request):
    profile = request.user.employeeprofile
    records = Attendance.objects.filter(employee=profile).order_by('-date')
    return render(request, 'employee/attendance_report.html', {'records': records})


def my_c_offs(request):
    employee = request.user.employeeprofile
    balance = CompOffBalance.objects.filter(employee=employee).first()
    earned_offs = CompensatoryOff.objects.filter(employee=employee, approved=True)
    return render(request, 'timesheet/my_c_offs.html', {
        'balance': balance,
        'earned_offs': earned_offs,
    })


# employee/views/attendance_views.py



@login_required
def attendance_c_off_report(request):
    employee = request.user.employeeprofile
    today = now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    total_working_days = sum(
        1 for i in range((end_date - start_date).days + 1)
        if (start_date + timedelta(days=i)).weekday() < 5
    )

    timesheets = Timesheet.objects.filter(
        employee=employee,
        status='Approved',
        date__range=(start_date, end_date)
    )

    attended_days = {ts.date for ts in timesheets if ts.date.weekday() < 5}
    attendance_count = len(attended_days)

    try:
        c_off_balance = CompOffBalance.objects.get(employee=employee).balance
    except CompOffBalance.DoesNotExist:
        c_off_balance = 0

    # Get C-Off form
    form = CompOffApplicationForm(employee=employee)
    if request.method == 'POST':
        form = CompOffApplicationForm(request.POST, employee=employee)
        if form.is_valid():
            application = form.save(commit=False)
            application.employee = employee
            application.save()
            messages.success(request, "C-Off request submitted.")
            return redirect('employee:attendance-c-off-report')

    context = {
        'month': month,
        'year': year,
        'working_days': total_working_days,
        'attendance_days': attendance_count,
        'attendance_percent': round((attendance_count / total_working_days) * 100, 1) if total_working_days else 0,
        'c_off_balance': c_off_balance,
        'available_months': [(m, date(year, m, 1).strftime('%B')) for m in range(1, 13)],
        'available_years': list(range(today.year - 1, today.year + 2)),
        'form': form,
        'records': timesheets.order_by('date'),  # Optional: show each approved day
    }

    past_applications = CompOffApplication.objects.filter(employee=employee).order_by('-date_requested')

    context.update({
        'form': form,
        'past_applications': past_applications,
})
    return render(request, 'employee/attendance_c_off_report.html', context)
