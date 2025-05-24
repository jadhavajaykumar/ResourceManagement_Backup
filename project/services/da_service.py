# project/services/da_service.py

from decimal import Decimal
from datetime import datetime
from typing import Tuple, Optional
from project.models import DASetting
from timesheet.models import Timesheet


def calculate_total_hours(time_from, time_to) -> float:
    """Calculate total hours between two time values."""
    delta = datetime.combine(datetime.today(), time_to) - datetime.combine(datetime.today(), time_from)
    return delta.total_seconds() / 3600


def get_total_local_hours_on_date(employee, current_date):
    """Get total hours worked by employee on local projects for a single date."""
    entries = Timesheet.objects.filter(employee=employee, date=current_date, project__location_type__name__iexact='Local')
    total = 0
    for e in entries:
        total += calculate_total_hours(e.time_from, e.time_to)
    return total


def get_domestic_days_worked(employee, project):
    """Count number of distinct days employee worked on domestic project."""
    return Timesheet.objects.filter(
        employee=employee,
        project=project,
        project__location_type__name__iexact='Domestic'
    ).values('date').distinct().count()


def calculate_da(timesheet) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Centralized DA calculation logic.
    Returns: (da_amount, currency)
    """
    project = timesheet.project
    location = project.location_type.name.lower()
    currency = project.currency or 'INR'

    total_hours = calculate_total_hours(timesheet.time_from, timesheet.time_to)

    if location == 'office':
        return None, None

    if location == 'local':
        total_day_hours = get_total_local_hours_on_date(timesheet.employee, timesheet.date)
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if setting and total_day_hours >= setting.min_hours:
            return setting.da_amount, currency
        return None, None

    if location == 'domestic':
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if not setting:
            return None, None

        days_worked = get_domestic_days_worked(timesheet.employee, project)
        extended_da = Decimal(150) if days_worked >= 60 else Decimal(0)
        return setting.da_amount + extended_da, currency

    if location == 'international':
        base_da = project.da_rate_per_day or Decimal(0)
        extended_da = Decimal(0)

        if project.extended_hours_threshold and total_hours > project.extended_hours_threshold:
            extended_da = project.extended_hours_da_rate or Decimal(0)

        return base_da + extended_da, currency

    return None, None
