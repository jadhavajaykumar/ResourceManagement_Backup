# project/services/earning_service.py

def calculate_earning(timesheet):
    """
    Calculate earnings based on project type, location, and timesheet hours.
    - Service projects can be hourly or daily.
    - Turnkey projects return zero (budget-based revenue).
    """
    project = timesheet.project

    if project.project_type.name.lower() == 'service' and project.location_type.name.lower() == 'international':
        if project.rate_type == 'Hourly':
            return timesheet.hours * project.rate_value
        elif project.rate_type == 'Daily':
            return project.rate_value

    elif project.project_type.name.lower() == 'turnkey':
        return 0

    return 0
