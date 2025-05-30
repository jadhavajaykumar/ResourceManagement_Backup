from timesheet.models import Timesheet
from django.db.models import Min, Max
from django.db import transaction

def merge_all_for_employee_date(employee, date):
    projects = Timesheet.objects.filter(
        employee=employee,
        date=date,
        status='Approved'
    ).values_list('project', flat=True).distinct()

    for project_id in projects:
        entries = Timesheet.objects.filter(
            employee=employee,
            date=date,
            project_id=project_id,
            status='Approved'
        ).order_by('time_from')

        if entries.count() <= 1:
            continue

        with transaction.atomic():
            earliest = entries.aggregate(Min('time_from'))['time_from__min']
            latest = entries.aggregate(Max('time_to'))['time_to__max']
            combined_desc = "\n".join(f"• {e.task_description.strip()}" for e in entries)

            primary = entries.first()
            Timesheet.objects.filter(id__in=entries.exclude(id=primary.id).values_list('id', flat=True)).delete()

            primary.time_from = earliest
            primary.time_to = latest
            primary.task_description = combined_desc
            primary.save()
