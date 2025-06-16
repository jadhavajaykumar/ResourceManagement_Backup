from datetime import date
from calendar import HTMLCalendar
from utils.currency import format_currency
from decimal import Decimal, InvalidOperation

class StyledCalendar(HTMLCalendar):
    def __init__(self, status_map):
        super().__init__()
        self.status_map = status_map

    def formatday(self, day, weekday, theyear, themonth):
        if day == 0:
            return '<td class="bg-light calendar-day"></td>'

        dt = date(theyear, themonth, day)
        day_data = self.status_map.get(dt, {})
        status = day_data.get('status', 'no_entry')
        hours = day_data.get('hours', '')
        da = day_data.get('da', None)
        currency = day_data.get('currency', '')

        # 🔄 Override status if it's weekend and hours are logged
        if weekday in (5, 6):  # Saturday=5, Sunday=6
            try:
                if float(hours) > 0:
                    status = 'coff'
            except (TypeError, ValueError):
                pass  # Leave status as-is if hours is invalid

        css_class = {
            'approved': 'bg-success text-white',
            'submitted': 'bg-info text-white',
            'partial': 'bg-warning text-dark',
            'incomplete': 'bg-warning text-dark',
            'coff': 'bg-primary text-white',
            'absent': 'bg-danger text-white',
            'not_submitted': 'bg-light text-muted',
            'no_entry': 'bg-light text-muted',
        }.get(status, 'bg-light')

        hours_badge = f'<div class="badge bg-dark text-white mt-1">{hours} hrs</div>' if hours else ''

        # ✅ DA display with safe formatting
        da_display = ''
        if da:
            try:
                da_amount = Decimal(str(da))
                da_display = format_currency(da_amount, currency)
            except (InvalidOperation, TypeError, ValueError):
                da_display = f"{da} {currency}"

        da_badge = f'<div class="badge bg-secondary text-white mt-1">{da_display}</div>' if da_display else ''
        
                # ✅ C-Off badge logic (only weekends)
        coff_badge = ''
        try:
            if weekday in (5, 6) and float(hours) > 0:
                if float(hours) < 4:
                    coff_badge = '<div class="badge bg-info text-white mt-1">0.5 C-Off</div>'
                else:
                    coff_badge = '<div class="badge bg-info text-white mt-1">1 C-Off</div>'
        except (TypeError, ValueError):
            pass


        return f'''
        <td class="calendar-day {css_class}">
            <div class="d-flex flex-column">
                <strong>{day}</strong>
                <small class="text-capitalize">{status.replace("_", " ")}</small>
                {hours_badge}
                {da_badge}
                {coff_badge}
            </div>
        </td>
        '''


    def formatweek(self, theweek, theyear, themonth):
        return '<tr>' + ''.join(
            self.formatday(d, wd, theyear, themonth) for (d, wd) in theweek
        ) + '</tr>'

    def formatmonth(self, theyear, themonth, withyear=True):
        weeks = self.monthdays2calendar(theyear, themonth)
        week_header = self.formatweekheader()
        weeks_html = ''.join(self.formatweek(week, theyear, themonth) for week in weeks)

        return f'''
        <style>
            .calendar-day {{
                padding: 8px;
                border-radius: 8px;
                min-height: 90px;
                font-size: 0.85rem;
                vertical-align: top;
            }}
            .calendar-day:hover {{
                transform: scale(1.05);
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                transition: all 0.2s ease;
            }}
            .calendar table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 6px;
            }}
            .calendar th {{
                padding: 10px;
                background-color: #f8f9fa;
                font-weight: 600;
            }}
        </style>
        <div class="calendar">
            <table class="table table-bordered">
                <thead><tr>{week_header}</tr></thead>
                <tbody>{weeks_html}</tbody>
            </table>
        </div>
        '''
