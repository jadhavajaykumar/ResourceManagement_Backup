from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from employee.models import AuditLog
from timesheet.models import Attendance, TimeSlot
from project.services.da_service import calculate_da
import logging
logger = logging.getLogger(__name__)
def calculate_total_hours(timesheet):
    """Calculate total hours from all time slots"""
    if hasattr(timesheet, 'time_slots') and timesheet.time_slots.exists():
        total_hours = sum(float(slot.hours) for slot in timesheet.time_slots.all())
    else:
        raise ValidationError("No time slots provided")

    if total_hours <= 0:
        raise ValidationError("Invalid time duration - must be positive")
    if total_hours > 24:
        raise ValidationError("Shift duration cannot exceed 24 hours")

    return round(total_hours, 2)

def update_attendance(timesheet, total_hours):
    """Update attendance for the start date only"""
    is_weekend = timesheet.date.weekday() >= 5
    attendance_date = timesheet.date  # Always use start date

    # Adjust attendance logic based on total hours
    if total_hours >= 8:
        status = 'Present'
    elif total_hours >= 4:
        status = 'Half Day' if not is_weekend else 'Present'
    else:
        status = 'Absent' if not is_weekend else 'Half Day'

    Attendance.objects.update_or_create(
        employee=timesheet.employee,
        date=attendance_date,
        defaults={'status': status}
    )

def log_audit(timesheet):
    """Log audit entry for submitted timesheet."""
    project_names = ", ".join(
        {slot.project.name for slot in timesheet.time_slots.all()}
    )
    AuditLog.objects.create(
        user=timesheet.employee.user,
        action="Timesheet Submitted",
        details=f"Timesheet for {project_names} on {timesheet.date}"
    )

# timesheet/services/timesheet_service.py
# ... existing imports ...

# timesheet/services/timesheet_service.py

# timesheet/services/timesheet_service.py

# timesheet/services/timesheet_service.py
# ... existing imports ...

def process_timesheet_save(timesheet):
    """Core business logic for timesheet saving."""
    try:
        total_hours = calculate_total_hours(timesheet)
        timesheet.total_hours = total_hours
        timesheet.save()

        # Get time slots through the correct relation
        slots = list(timesheet.time_slots.all())

        # Ensure slot_date is recorded
        for slot in slots:
            if not slot.slot_date:
                slot.slot_date = timesheet.date
                slot.save(update_fields=['slot_date'])

        # Calculate DA with error handling
        if slots:
            try:
                first_slot = slots[0]
                da_amount, da_currency = calculate_da(first_slot)
                timesheet.daily_allowance_amount = da_amount
                timesheet.daily_allowance_currency = da_currency
                timesheet.save()
            except Exception as da_error:
                logger.error(f"DA calculation error: {da_error}")

        # Check for office slots using safe access
        has_office_slot = False
        for slot in slots:
            try:
                if (slot.project and 
                    slot.project.location_type and 
                    slot.project.location_type.name == 'Office'):
                    has_office_slot = True
                    break
            except Exception as e:
                logger.error(f"Error checking office slot: {e}")
        
        if has_office_slot:
            try:
                update_attendance(timesheet, total_hours)
            except Exception as att_error:
                logger.error(f"Attendance update error: {att_error}")

        log_audit(timesheet)
        
    except Exception as e:
        logger.exception("Critical error in process_timesheet_save")
        raise ValidationError(f"System error: {e}")

