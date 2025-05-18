from decimal import Decimal
from datetime import datetime
from project.models import DASetting

def calculate_total_hours(time_from, time_to):
    return (datetime.combine(datetime.today(), time_to) - datetime.combine(datetime.today(), time_from)).seconds / 3600

def calculate_da(timesheet):
    project = timesheet.project
    total_hours = calculate_total_hours(timesheet.time_from, timesheet.time_to)

    da_amount = None
    currency = 'INR'

    if project.location_type.name.lower() == 'office':
        return None, None

    elif project.location_type.name.lower() == 'local':
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if setting and total_hours >= setting.min_hours:
            da_amount = setting.da_amount

    elif project.location_type.name.lower() == 'domestic':
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if setting:
            da_amount = setting.da_amount

    elif project.location_type.name.lower() == 'international':
        base_da = project.da_rate_per_day or Decimal(0)
        extended_da = Decimal(0)

        if project.extended_hours_threshold and total_hours > project.extended_hours_threshold:
            extended_da = project.extended_hours_da_rate or Decimal(0)

        da_amount = base_da + extended_da
        currency = project.currency or 'USD'

    return da_amount, currency
