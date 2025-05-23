# timesheet/services/timesheet_service.py

from datetime import datetime
from employee.models import AuditLog, LeaveBalance
from timesheet.models import Attendance
from project.services.da_service import calculate_da


def calculate_total_hours(timesheet):
    """Compute total hours worked from time_from and time_to."""
    start = datetime.combine(timesheet.date, timesheet.time_from)
    end = datetime.combine(timesheet.date, timesheet.time_to)
    return (end - start).total_seconds() / 3600


def update_attendance(timesheet, total_hours):
    """Update attendance and comp-off for office-based entries."""
    is_weekend = timesheet.date.weekday() >= 5
    status = 'Absent'
    comp_off = 0

    if total_hours >= 8:
        status = 'Present'
    elif total_hours >= 4:
        status = 'Half Day' if not is_weekend else 'Present'
        comp_off = 1 if is_weekend else 0
    else:
        status = 'Absent' if not is_weekend else 'Half Day'
        comp_off = 0.5 if is_weekend else 0

    Attendance.objects.update_or_create(
        employee=timesheet.employee,
        date=timesheet.date,
        defaults={'status': status}
    )

    if comp_off > 0:
        leave_balance, _ = LeaveBalance.objects.get_or_create(employee=timesheet.employee)
        leave_balance.c_off += comp_off
        leave_balance.save()


def log_audit(timesheet):
    """Log audit entry for submitted timesheet."""
    AuditLog.objects.create(
        user=timesheet.employee.user,
        action="Timesheet Submitted",
        details=f"Timesheet for {timesheet.project.name} on {timesheet.date}"
    )


def process_timesheet_save(timesheet):
    """Core business logic for timesheet saving."""
    total_hours = calculate_total_hours(timesheet)
    timesheet.total_hours = total_hours  # Optional: if total_hours is stored

    # Calculate and assign DA
    da_amount, da_currency = calculate_da(timesheet)
    timesheet.daily_allowance_amount = da_amount
    timesheet.daily_allowance_currency = da_currency

    # Only update attendance for office entries
    if getattr(timesheet.project, 'location', '') == 'Office':
        update_attendance(timesheet, total_hours)

    log_audit(timesheet)
