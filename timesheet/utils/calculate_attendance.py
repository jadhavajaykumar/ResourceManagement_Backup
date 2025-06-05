from datetime import time
from django.utils import timezone
from timesheet.models import Timesheet, Attendance

def calculate_attendance(employee, date):
    """
    Calculate attendance status considering night shifts
    Returns: 'Present', 'Half Day', or 'Absent'
    """
    timesheets = Timesheet.objects.filter(
        employee=employee,
        date=date,
        status='Approved'
    ).order_by('time_from')
    
    total_hours = 0
    for entry in timesheets:
        if entry.time_to < entry.time_from:  # Night shift
            # Calculate hours spanning midnight
            hours = ((24 - entry.time_from.hour) + entry.time_to.hour) + \
                   ((entry.time_to.minute - entry.time_from.minute)/60)
        else:
            hours = (entry.time_to.hour - entry.time_from.hour) + \
                   ((entry.time_to.minute - entry.time_from.minute)/60)
        
        total_hours += hours
    
    # Determine attendance status
    if total_hours >= 8:
        return 'Present'
    elif total_hours >= 4:
        return 'Half Day'
    return 'Absent'