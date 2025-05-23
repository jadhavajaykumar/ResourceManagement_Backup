# timesheet/services/export_service.py

import csv
from django.http import HttpResponse

def export_timesheets_to_csv(timesheets, filename="timesheets.csv"):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Project', 'Task', 'Time From', 'Time To', 'Description', 'Status'])

    for entry in timesheets:
        writer.writerow([
            entry.date,
            entry.project.name if entry.project else '',
            entry.task.name if entry.task else '',
            entry.time_from,
            entry.time_to,
            entry.task_description,
            entry.status
        ])

    return response
