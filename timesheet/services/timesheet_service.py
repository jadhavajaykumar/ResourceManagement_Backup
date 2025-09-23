from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from employee.models import AuditLog
from timesheet.models import Attendance, TimeSlot, Holiday
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



def process_timesheet_save(timesheet):
    """
    Core business logic for timesheet saving and post-save housekeeping.
    - Recalculates total hours
    - If timesheet has zero slots -> delete timesheet + clean attendance / coff
    - Updates Attendance, DA, creates C-Off if weekend/holiday and not duplicate
    - Logs audit
    - Raises ValidationError for invalid states (e.g. >24h total)
    """
    try:
        # If timesheet has been approved, disallow changes where necessary is checked earlier in views.
        # First guard: if timesheet exists in DB and status is Approved, we shouldn't be here for deletions.
        if hasattr(timesheet, 'status') and timesheet.pk and timesheet.status == 'Approved':
            # We still allow saving non-deleting edits but delete protection should already be enforced by views.
            logger.debug(f"Timesheet {timesheet.id} is Approved; ensure view prevented destructive changes.")

        slots = list(timesheet.time_slots.all())

        # If no slots remain (e.g. user deleted all rows) -> delete timesheet and cleanup
        if not slots:
            if timesheet.pk:
                logger.info(f"No time slots found for timesheet {timesheet.pk} on {timesheet.date} — removing timesheet and cleaning attendance/C-off.")
                _delete_timesheet_cleanup(timesheet)
                return  # nothing further to do
            else:
                raise ValidationError("No time slots provided")

        # compute total hours and validate
        total_hours = calculate_total_hours(timesheet)
        if total_hours <= 0:
            raise ValidationError("Invalid time duration - must be positive")
        if total_hours > 24:
            raise ValidationError("Shift duration cannot exceed 24 hours")

        timesheet.total_hours = total_hours
        timesheet.save()

        # Ensure slot_date present for each slot (use timesheet.date as authoritative)
        for slot in slots:
            changed_fields = []
            if not slot.slot_date:
                slot.slot_date = timesheet.date
                changed_fields.append('slot_date')
            # Keep worked_onsite as-is (checkbox stored on slot)
            # Save only if changed
            if changed_fields:
                slot.save(update_fields=changed_fields)

        # daily allowance (DA) calculation — try using first slot (safe)
        try:
            first_slot = slots[0]
            da_amount, da_currency = calculate_da(first_slot)
            timesheet.daily_allowance_amount = da_amount
            timesheet.daily_allowance_currency = da_currency
            timesheet.save(update_fields=['daily_allowance_amount', 'daily_allowance_currency'])
        except Exception as e:
            logger.exception(f"DA calculation failed for timesheet {timesheet.pk}: {e}")

        # Check if any slot was onsite (either via slot.worked_onsite or project location)
        try:
            has_onsite = any(getattr(s, 'worked_onsite', False) for s in slots)
        except Exception:
            has_onsite = False

        # Update Attendance only if there is onsite work OR by previous logic (keep existing logic)
        try:
            # reuse your update_attendance logic but pass timesheet/total_hours
            is_weekend = timesheet.date.weekday() >= 5
            attendance_date = timesheet.date
            status = 'Absent'
            if total_hours >= 8:
                status = 'Present'
            elif total_hours >= 4:
                status = 'Half Day' if not is_weekend else 'Present'
            else:
                status = 'Absent' if not is_weekend else 'Half Day'

            # If there was onsite work we create/update attendance (previous behavior)
            if has_onsite or total_hours > 0:
                Attendance.objects.update_or_create(
                    employee=timesheet.employee,
                    date=attendance_date,
                    defaults={'status': status}
                )
        except Exception as e:
            logger.error(f"Attendance update failed for timesheet {timesheet.pk}: {e}")

        # C-off logic — create only if weekend/holiday and not duplicate
        try:
            if isinstance(timesheet.date, str):
                timesheet.date = datetime.fromisoformat(timesheet.date).date()

            weekday = timesheet.date.weekday()
            is_weekend = weekday in [5, 6]
            is_holiday = Holiday.objects.filter(date=timesheet.date).exists()

            if (is_weekend or is_holiday):
                credited_days = 0.0
                if total_hours >= 4:
                    credited_days = 1.0
                elif total_hours > 0:
                    credited_days = 0.5

                if credited_days > 0:
                    # avoid duplicate for same timesheet
                    if not CompensatoryOff.objects.filter(timesheet=timesheet).exists():
                        CompensatoryOff.objects.create(
                            employee=timesheet.employee,
                            date_earned=timesheet.date,
                            hours_logged=total_hours,
                            approved=False,
                            credited_days=credited_days,
                            timesheet=timesheet
                        )
        except Exception as e:
            logger.error(f"C-Off creation failed for timesheet {timesheet.pk}: {e}")

        # Final audit
        try:
            project_names = ", ".join({slot.project.name for slot in slots if getattr(slot, 'project', None)})
            AuditLog.objects.create(
                user=timesheet.employee.user,
                action="Timesheet Saved",
                details=f"Timesheet for {project_names} on {timesheet.date} saved (hours={timesheet.total_hours})"
            )
        except Exception as e:
            logger.error(f"Audit logging failed for timesheet {timesheet.pk}: {e}")

    except ValidationError:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in process_timesheet_save")
        raise ValidationError(f"System error: {e}")
