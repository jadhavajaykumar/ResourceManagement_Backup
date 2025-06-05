from datetime import time, datetime
from datetime import datetime
# Time slot definitions (you may move this to utils.py if preferred)
TIME_SLOTS = [
    (time(9, 0), time(11, 0)),
    (time(11, 0), time(13, 0)),
    (time(13, 0), time(13, 30)),  # lunch
    (time(13, 30), time(15, 30)),
    (time(15, 30), time(17, 30)),
    (time(17, 30), time(18, 15)),
]

def get_current_slot():
    now = datetime.now().time()
    for start, end in TIME_SLOTS:
        if start <= now <= end:
            return start, end
    return time(9, 0), time(11, 0)  # default fallback
    


def get_slot_date(timesheet_date, from_time):
    """Returns the real calendar date for the slot start."""
    from_dt = datetime.combine(timesheet_date, from_time)
    return from_dt.date()
    


def merge_timesheet_entries(entries):
    grouped = defaultdict(lambda: {'start': None, 'end': None, 'tasks': []})

    for entry in entries:
        key = (entry.date, entry.project.project_name)
        start = datetime.strptime(entry.start_time.strftime('%H:%M'), '%H:%M')
        end = datetime.strptime(entry.end_time.strftime('%H:%M'), '%H:%M')

        if grouped[key]['start'] is None or start < grouped[key]['start']:
            grouped[key]['start'] = start
        if grouped[key]['end'] is None or end > grouped[key]['end']:
            grouped[key]['end'] = end
        grouped[key]['tasks'].append(entry.task_description)

    merged = []
    for (date, project), values in grouped.items():
        merged.append({
            'date': date,
            'project': project,
            'start_time': values['start'].strftime('%H:%M'),
            'end_time': values['end'].strftime('%H:%M'),
            'tasks': values['tasks'],
        })

    return merged
    
    