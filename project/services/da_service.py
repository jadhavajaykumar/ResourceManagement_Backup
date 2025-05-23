# project/services/da_service.py

from decimal import Decimal
from datetime import datetime
from typing import Tuple, Optional
from project.models import DASetting
from timesheet.models import Timesheet


def calculate_total_hours(time_from, time_to) -> float:
    """
    Calculate total hours between two time values.
    """
    return (datetime.combine(datetime.today(), time_to) - datetime.combine(datetime.today(), time_from)).seconds / 3600


def calculate_da(timesheet) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Centralized DA calculation logic.
    Returns: (da_amount, currency)
    """
    project = timesheet.project
    location = project.location_type.name.lower()
    currency = 'INR'

    total_hours = (
        timesheet.hours
        if hasattr(timesheet, 'hours') and timesheet.hours is not None
        else calculate_total_hours(timesheet.time_from, timesheet.time_to)
    )

    if location == 'office':
        return None, None

    if location == 'local':
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if setting and total_hours >= setting.min_hours:
            return setting.da_amount, currency
        return None, None

    if location == 'domestic':
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if setting:
            return setting.da_amount, currency
        return None, None

    if location == 'international':
        base_da = project.da_rate_per_day or Decimal(0)
        extended_da = Decimal(0)

        if project.extended_hours_threshold and total_hours > project.extended_hours_threshold:
            extended_da = project.extended_hours_da_rate or Decimal(0)

        return base_da + extended_da, project.currency or 'USD'

    return None, None



def is_weekend_da_eligible(employee, project, current_date):
    """
    Check if the employee is eligible for weekend DA based on next week's domestic project entries.
    """
    next_week_start = current_date + timedelta(days=(7 - current_date.weekday()))
    next_week_end = next_week_start + timedelta(days=6)

    entries = Timesheet.objects.filter(
        employee=employee,
        date__range=(next_week_start, next_week_end),
        project__location_type__name='Domestic'
    )
    return entries.exists()
