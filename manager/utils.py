# manager/utils.py

from timesheet.models import Timesheet
from expenses.models import Expense
from datetime import date
from django.db.models import Sum, F, ExpressionWrapper, DurationField

def calculate_project_progress(project):
    timesheets = Timesheet.objects.filter(project=project, status='Approved')
    expenses = Expense.objects.filter(project=project, status='Approved')

    total_expense = expenses.aggregate(total=Sum('amount'))['total'] or 0

    if project.type == 'Service':
        # Count distinct days (billable days)
        days_worked = timesheets.values('employee', 'date').distinct().count()
        earnings = days_worked * float(project.daily_rate or 0)
    else:
        earnings = None  # Not applicable

    progress = {
        'total_expense': total_expense,
        'days_worked': days_worked if project.type == 'Service' else None,
        'earnings': earnings,
        'budget_utilized': (total_expense / float(project.budget)) * 100 if project.type == 'Turnkey' and project.budget else None,
    }
    return progress
