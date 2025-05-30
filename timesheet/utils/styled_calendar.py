from datetime import date
from calendar import HTMLCalendar

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

        hours_badge = f'<div class="badge bg-dark text-white mt-1">{hours}</div>' if hours else ''
        
        return f'''
        <td class="calendar-day {css_class}">
            <div class="d-flex flex-column">
                <strong>{day}</strong>
                <small class="text-capitalize">{status.replace("_", " ")}</small>
                {hours_badge}
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
                min-height: 80px;
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