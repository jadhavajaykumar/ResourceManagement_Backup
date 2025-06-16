from collections import defaultdict 
from datetime import date
from calendar import monthrange
from decimal import Decimal, InvalidOperation
from django.utils import timezone

from timesheet.models import Timesheet, Attendance
from expenses.models import DailyAllowance

import re

def get_timesheet_calendar_data(employee, year, month):
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # Load timesheets for the month
    entries = Timesheet.objects.filter(
        employee=employee,
        date__range=(start_date, end_date)
    ).prefetch_related('time_slots__project__location_type')

    # Load DA records for the month
    da_entries = DailyAllowance.objects.filter(
        employee=employee,
        date__range=(start_date, end_date)
    )

    # Build initial day_data
    day_data = defaultdict(lambda: {
        'status': 'no_entry',
        'hours': 0,
        'approved_hours': 0,
        'is_weekend': False,
        'da': None,
        'currency': '',
    })

    # Sum up timesheet hours
    for entry in entries:
        key = entry.date
        duration = entry.get_total_hours()
        day_data[key]['hours'] += duration

        if entry.status == 'Approved':
            day_data[key]['approved_hours'] += duration

            if entry.daily_allowance_amount:
                day_data[key]['da'] = f"{entry.daily_allowance_currency or 'INR'} {entry.daily_allowance_amount}"
            else:
                # Try fallback from DailyAllowance
                da = DailyAllowance.objects.filter(
                    timesheet=entry,
                    date=entry.date,
                    employee=entry.employee
                ).first()
                if da:
                    day_data[key]['da'] = f"{da.currency or 'INR'} {da.da_amount}"

    # Attach DA from DailyAllowance model
    for da in da_entries:
        key = da.date
        existing_da = extract_numeric_da(day_data[key]['da']) if day_data[key].get('da') else Decimal('0.0')
        if Decimal(da.da_amount) > existing_da:
            day_data[key]['da'] = f"{da.currency or 'INR'} {da.da_amount}"

            day_data[key]['da'] = da.da_amount
            day_data[key]['currency'] = da.currency or 'INR'

    # Final status logic
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



# Regex to extract only the numeric part from formatted DA strings
def extract_numeric_da(da_string):
    try:
        number = re.search(r'(\d+(\.\d+)?)', da_string)
        return Decimal(number.group(1)) if number else Decimal('0.0')
    except (InvalidOperation, AttributeError):
        return Decimal('0.0')
