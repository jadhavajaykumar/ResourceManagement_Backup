from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Q, Count
from timesheet.models import Timesheet
from project.models import Project
from django.utils import timezone
from datetime import timedelta
from project.services.da_calculator import calculate_da

def get_project_profitability(project_id):
    project = Project.objects.get(id=project_id)

    # Calculate total DA claimed by employees
    total_da = Timesheet.objects.filter(
        project=project,
        status='Approved',
        daily_allowance_amount__isnull=False
    ).aggregate(total=Sum('daily_allowance_amount'))['total'] or 0

    # Calculate total project expenses from expenses module (optional link)
    # Assume you have a related expenses model
    from expenses.models import EmployeeExpense
    total_expenses = EmployeeExpense.objects.filter(
        project=project,
        status='Approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate earnings
    if project.project_type.name.lower() == 'service':
        timesheets = Timesheet.objects.filter(project=project, status='Approved')
        if project.rate_type == 'Hourly':
            total_hours = timesheets.annotate(
                hours=ExpressionWrapper(
                    (F('time_to') - F('time_from')),
                    output_field=DecimalField()
                )
            ).count()  # Assuming direct hours field is available; adjust as per actual
            earnings = total_hours * project.rate_value
        elif project.rate_type == 'Daily':
            working_days = timesheets.values('date').distinct().count()
            earnings = working_days * project.rate_value
        else:
            earnings = 0
    elif project.project_type.name.lower() == 'turnkey':
        earnings = project.budget
    else:
        earnings = 0

    # Net profit
    profit = earnings - total_expenses - total_da

    # Percentages
    expense_percent = (total_expenses / earnings * 100) if earnings > 0 else 0
    profit_percent = (profit / earnings * 100) if earnings > 0 else 0

    return {
        'project_name': project.name,
        'total_earnings': earnings,
        'total_expenses': total_expenses,
        'total_da_claimed': total_da,
        'net_profit': profit,
        'expense_percentage': round(expense_percent, 2),
        'profit_percentage': round(profit_percent, 2),
    }



def get_employee_da_claims(project_id):
    timesheets = Timesheet.objects.filter(project_id=project_id, status='Approved')

    # You can re-calculate DA if needed using centralized service
    recalculated_claims = []
    for ts in timesheets:
        da_amount, currency = calculate_da(ts)
        recalculated_claims.append({
            'employee': ts.employee.user.get_full_name(),
            'date': ts.date,
            'calculated_da': da_amount,
            'currency': currency,
        })

    return recalculated_claims



def get_timesheet_earning_report(project_id):
    project = Project.objects.get(id=project_id)
    timesheets = Timesheet.objects.filter(project=project, status='Approved')

    report = []

    for ts in timesheets:
        total_hours = (datetime.combine(ts.date, ts.time_to) - datetime.combine(ts.date, ts.time_from)).seconds / 3600
        earning = 0
        if project.rate_type == 'Hourly':
            earning = total_hours * project.rate_value
        elif project.rate_type == 'Daily':
            earning = project.rate_value

        report.append({
            'employee': ts.employee.user.get_full_name(),
            'date': ts.date,
            'hours': total_hours,
            'earning': earning,
            'da_claimed': ts.daily_allowance_amount,
        })

    return report
