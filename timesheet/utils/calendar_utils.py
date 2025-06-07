from collections import defaultdict 
from datetime import datetime, date, timedelta
from calendar import monthrange
from django.utils import timezone
from timesheet.models import Timesheet, Attendance


from decimal import Decimal

from project.services.da_service import calculate_da

def get_timesheet_calendar_data(employee, year, month):
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    entries = Timesheet.objects.filter(
        employee=employee,
        date__range=(start_date, end_date)
    ).prefetch_related(
        'time_slots__project__location_type'
)

    day_data = defaultdict(lambda: {
        'status': 'no_entry',
        'hours': 0,
        'approved_hours': 0,
        'is_weekend': False,
        'da': None
    })

    for entry in entries:
        key = entry.date
        duration = entry.get_total_hours()
        day_data[key]['hours'] += duration

        if entry.status == 'Approved':
            day_data[key]['approved_hours'] += duration

            # Add DA amount if applicable
            # Use already saved DA amount from the timesheet
            if entry.daily_allowance_amount:
                if not day_data[key]['da'] or Decimal(entry.daily_allowance_amount) > Decimal(day_data[key]['da']):
                    day_data[key]['da'] = round(Decimal(entry.daily_allowance_amount), 2)


    for day in range(1, end_date.day + 1):
        dt = date(year, month, day)
        data = day_data[dt]

        if data['hours'] == 0:
            data['status'] = 'no_entry'
        elif data['hours'] >= 8.5:
            data['status'] = 'approved' if data['approved_hours'] >= 8.5 else 'submitted'
        elif 0 < data['hours'] < 8.5:
            data['status'] = 'incomplete'

        data['is_weekend'] = dt.weekday() >= 5
        if data['is_weekend'] and data['approved_hours'] >= 4:
            data['status'] = 'coff'

        if Attendance.objects.filter(employee=employee, date=dt, status='Absent').exists():
            data['status'] = 'absent'

    return day_data
