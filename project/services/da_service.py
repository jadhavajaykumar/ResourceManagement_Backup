# project/services/da_service.py

# project/services/da_service.py

from decimal import Decimal
from datetime import datetime
from typing import Tuple, Optional
from project.models import DASetting
from timesheet.models import TimeSlot
from expenses.models import GlobalDASettings, CountryDASetting


def calculate_total_hours(time_from, time_to) -> float:
    """Calculate total hours between two time values."""
    delta = datetime.combine(datetime.today(), time_to) - datetime.combine(datetime.today(), time_from)
    return delta.total_seconds() / 3600


def get_total_local_hours_on_date(employee, date):
    """Sum total hours worked by employee on local projects for a given date."""
    slots = TimeSlot.objects.filter(
        employee=employee,
        slot_date=date,
        project__location_type__name__iexact='Local'
    )
    return sum(slot.hours for slot in slots)


def get_domestic_days_worked(employee, project):
    """Count number of distinct days employee worked on a domestic project."""
    slots = TimeSlot.objects.filter(
        employee=employee,
        project=project,
        project__location_type__name__iexact='Domestic'
    ).values('slot_date').distinct()
    return slots.count()






from decimal import Decimal

def calculate_da(slot):
    """
    Calculate Daily Allowance based on project type and configuration.
    Works for Local, Domestic, and International projects.
    """

    timesheet = getattr(slot, 'timesheet', None)
    if not timesheet:
        raise ValueError("Timeslot is not linked to a timesheet")

    project = slot.project
    location_type = project.location_type.name if project.location_type else None
    da_type = project.da_type
    da_rate = project.da_rate_per_unit or Decimal("0.0")
    weekday = slot.slot_date.weekday()

    total_hours = sum(s.hours for s in slot.timesheet.time_slots.filter(project=project))

    # Default currency fallback
    currency = project.currency or "INR"

    if location_type == "Local":
        # Local project DA: flat rate per day
        return Decimal("300.00"), currency

    elif location_type == "Domestic":
        # Domestic project DA: ₹600 per day
        return Decimal("600.00"), currency

    elif location_type == "International":
        # Weekend / off-day DA (Sat/Sun)
        if weekday in [5, 6] and total_hours > 0:
            return project.off_day_da_rate or Decimal("0.0"), currency

        if da_type == "Hourly":
            return da_rate * Decimal(str(total_hours)), currency

        elif da_type == "Daily":
            return da_rate, currency
    print(f"📌 Calculated DA: {da_amount} {currency} for {project.name}")

    # Default fallback (in case config is incomplete)
    return Decimal("0.0"), currency



    