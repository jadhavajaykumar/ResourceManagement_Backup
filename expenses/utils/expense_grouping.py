from collections import defaultdict
from expenses.models import DailyAllowance

def group_expenses_by_date_and_project(expenses):
    grouped = defaultdict(lambda: {'expenses': [], 'da': None})

    for exp in expenses:
        key = (exp.date, exp.project)
        grouped[key]['expenses'].append(exp)

    # Attach DA for each group (optional)
    for (date, project), data in grouped.items():
        da = DailyAllowance.objects.filter(date=date, project=project, employee=expenses[0].employee).first()
        data['da'] = da

    grouped_data = []
    for (date, project), data in grouped.items():
        grouped_data.append({
            'date': date,
            'project': project,
            'expenses': data['expenses'],
            'da': data['da']
        })

    # Sort by date descending
    return sorted(grouped_data, key=lambda x: x['date'], reverse=True)
