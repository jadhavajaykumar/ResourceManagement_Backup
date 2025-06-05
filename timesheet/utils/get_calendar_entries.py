from datetime import datetime, timedelta
from calendar import monthrange
from collections import defaultdict
from django.utils import timezone
from timesheet.models import Timesheet

def get_calendar_entries(employee, year, month):
    """Group all hours by the start date"""
    _, last_day = monthrange(year, month)
    start_date = datetime(year, month, 1).date()
    end_date = datetime(year, month, last_day).date()
    
    entries = Timesheet.objects.filter(
        employee=employee,
        date__gte=start_date - timedelta(days=1),  # Include previous day for night shifts
        date__lte=end_date,
        status='Approved'
    )
    
    calendar_data = defaultdict(float)
    for entry in entries:
        display_date = entry.date  # Always use the start date
        calendar_data[display_date] += entry.get_duration_hours()
    
    return dict(calendar_data)