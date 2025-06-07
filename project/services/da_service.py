# project/services/da_service.py

# project/services/da_service.py

from decimal import Decimal
from datetime import datetime
from typing import Tuple, Optional
from project.models import DASetting
from timesheet.models import TimeSlot


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


def calculate_da(slot: TimeSlot) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Centralized DA logic, now based on a TimeSlot (not Timesheet).
    Returns: (da_amount, currency)
    """
    project = slot.project
    location = project.location_type.name.lower()
    currency = project.currency or 'INR'

    if location == 'office':
        return None, None

    if location == 'local':
        total_day_hours = get_total_local_hours_on_date(slot.employee, slot.slot_date)
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if setting and total_day_hours >= setting.min_hours:
            return setting.da_amount, currency
        return None, None

    if location == 'domestic':
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if not setting:
            return None, None

        days_worked = get_domestic_days_worked(slot.employee, project)
        extended_da = Decimal(150) if days_worked >= 60 else Decimal(0)
        return setting.da_amount + extended_da, currency

    if location == 'international':
        base_da = project.da_rate_per_day or Decimal(0)
        extended_da = Decimal(0)

        if project.extended_hours_threshold and slot.hours > project.extended_hours_threshold:
            extended_da = project.extended_hours_da_rate or Decimal(0)

        return base_da + extended_da, currency

    return None, None
    