from django.db.models import Q
from datetime import timedelta

def calculate_da(timesheet):
    project = timesheet.project

    # Office Location - Always No DA
    if project.location_type.name.lower() == 'office':
        return 0

    # Local Project
    if project.location_type.name.lower() == 'local':
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        if timesheet.hours > setting.min_hours:
            return setting.da_amount
        else:
            return 0

    # Domestic Project
    if project.location_type.name.lower() == 'domestic':
        setting = DASetting.objects.filter(location_type=project.location_type).first()
        return setting.da_amount

    # International Projects
    if project.location_type.name.lower() == 'international':
        base_da = project.da_rate_per_day or 0
        extended_da = 0

        if project.extended_hours_threshold and timesheet.hours > project.extended_hours_threshold:
            extended_da = project.extended_hours_da_rate or 0

        return base_da + extended_da

    return 0


def calculate_earning(timesheet):
    project = timesheet.project

    if project.project_type.name.lower() == 'service' and project.location_type.name.lower() == 'international':
        if project.rate_type == 'Hourly':
            return timesheet.hours * project.rate_value
        elif project.rate_type == 'Daily':
            return project.rate_value
    elif project.project_type.name.lower() == 'turnkey':
        return 0  # For Turnkey, income is fixed as Budget
    return 0


def is_weekend_da_eligible(employee, project, current_date):
    next_week_start = current_date + timedelta(days=(7 - current_date.weekday()))
    next_week_end = next_week_start + timedelta(days=6)

    entries = Timesheet.objects.filter(
        employee=employee,
        date__range=(next_week_start, next_week_end),
        project__location_type__name='Domestic'
    )
    return entries.exists()
