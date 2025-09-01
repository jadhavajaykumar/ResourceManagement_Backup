from datetime import datetime
from django.db.models import Sum
from timesheet.models import Timesheet
from expenses.models import Expense


def calculate_project_progress(project):
    """Calculate basic progress metrics for a project."""
    timesheets = Timesheet.objects.filter(project=project, status='Approved')
    total_hours = sum(
        (datetime.combine(t.date, t.time_to) - datetime.combine(t.date, t.time_from)).total_seconds() / 3600
        for t in timesheets
    )
    days_worked = timesheets.values('date').distinct().count()

    earnings = 0
    if project.rate_value:
        if project.rate_type == 'Hourly':
            earnings = float(project.rate_value) * total_hours
        elif project.rate_type == 'Daily':
            earnings = float(project.rate_value) * days_worked

    total_expense = Expense.objects.filter(project=project, status='Approved').aggregate(
        total=Sum('amount')
    )['total'] or 0
    budget_utilized = (float(total_expense) / float(project.budget) * 100) if project.budget else 0

    return {
        'total_expense': total_expense,
        'earnings': earnings,
        'days_worked': days_worked,
        'budget_utilized': budget_utilized,
    }