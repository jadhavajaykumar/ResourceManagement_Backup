from collections import defaultdict 
from datetime import datetime, date, timedelta
from calendar import monthrange
from django.utils import timezone
from timesheet.models import Timesheet, Attendance

def get_timesheet_calendar_data(employee, year, month):
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    entries = Timesheet.objects.filter(
        employee=employee,
        date__range=(start_date, end_date)
    ).prefetch_related('time_slots')  # Prefetch for efficiency

    day_data = defaultdict(lambda: {
        'status': 'no_entry',
        'hours': 0,
        'approved_hours': 0,
        'is_weekend': False
    })

    # Aggregate all entries per date
    for entry in entries:
        key = entry.date
        
        # Use the model's method to get total hours
        duration = entry.get_total_hours()
        
        day_data[key]['hours'] += duration

        if entry.status == 'Approved':
            day_data[key]['approved_hours'] += duration

    for day in range(1, end_date.day + 1):
        dt = date(year, month, day)
        data = day_data[dt]  # initialize if not already

        # Threshold check
        if data['hours'] == 0:
            data['status'] = 'no_entry'
        elif data['hours'] >= 8.5:
            data['status'] = 'approved' if data['approved_hours'] >= 8.5 else 'submitted'
        elif 0 < data['hours'] < 8.5:
            data['status'] = 'incomplete'

        # Handle weekends
        data['is_weekend'] = dt.weekday() >= 5
        if data['is_weekend'] and data['approved_hours'] >= 4:
            data['status'] = 'coff'

        # Handle absents overriding other statuses
        if Attendance.objects.filter(employee=employee, date=dt, status='Absent').exists():
            data['status'] = 'absent'

    return day_data