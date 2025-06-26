from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from employee.models import AuditLog
from timesheet.models import Attendance, TimeSlot
from project.services.da_service import calculate_da
from timesheet.models import CompensatoryOff, CompOffBalance
import logging
from decimal import Decimal
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
                logger.info(f"Calculating DA for {timesheet.date} with total_hours={total_hours}")
                logger.info(f"First slot project: {first_slot.project}, slot_date: {first_slot.slot_date}")

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
                if (
                    slot.project and
                    slot.project.location_type and
                    slot.project.location_type.name == 'Office'
                ):
                    has_office_slot = True
                    break
            except Exception as e:
                logger.error(f"Error checking office slot: {e}")

        if has_office_slot:
            try:
                update_attendance(timesheet, total_hours)
            except Exception as att_error:
                logger.error(f"Attendance update error: {att_error}")

        # ✅ C-Off logic: apply only on weekends or holidays, and only once
        try:
            if isinstance(timesheet.date, str):
                timesheet.date = datetime.strptime(timesheet.date, "%Y-%m-%d").date()

            weekday = timesheet.date.weekday()
            is_weekend = weekday in [5, 6]
            is_holiday = Holiday.objects.filter(date=timesheet.date).exists()

            if is_weekend or is_holiday:
                credited_days = 0.0
                if total_hours >= 4:
                    credited_days = 1.0
                elif total_hours > 0:
                    credited_days = 0.5

                if credited_days > 0:
                    if not CompensatoryOff.objects.filter(timesheet=timesheet).exists():
                        CompensatoryOff.objects.create(
                            employee=timesheet.employee,
                            date_earned=timesheet.date,
                            hours_logged=total_hours,
                            approved=False,
                            credited_days=credited_days,
                            timesheet=timesheet
                        )

                        # Only create credit record (not balance update — approval pending)
                        logger.info(f"C-Off created: {credited_days} day(s) for {timesheet.employee} on {timesheet.date}")

        except Exception as coff_error:
            logger.error(f"C-Off evaluation error: {coff_error}")

        # Final audit
        log_audit(timesheet)

    except Exception as e:
        logger.exception("Critical error in process_timesheet_save")
        raise ValidationError(f"System error: {e}")
