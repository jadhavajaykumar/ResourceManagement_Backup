from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import datetime
from timesheet.models import Timesheet
from project.models import Project
from project.services.da_service import calculate_da


def get_project_profitability(project_id):
    project = Project.objects.get(id=project_id)

    total_da = Timesheet.objects.filter(
        project=project,
        status='Approved',
        daily_allowance_amount__isnull=False
    ).aggregate(total=Sum('daily_allowance_amount'))['total'] or 0

    from expenses.models import EmployeeExpense
    total_expenses = EmployeeExpense.objects.filter(
        project=project,
        status='Approved'
    ).aggregate(total=Sum('amount'))['total'] or 0

    if project.project_type.name.lower() == 'service':
        timesheets = Timesheet.objects.filter(project=project, status='Approved')
        if project.rate_type == 'Hourly':
            total_hours = timesheets.aggregate(hours=Sum('hours'))['hours'] or 0
            earnings = total_hours * project.rate_value
        elif project.rate_type == 'Daily':
            working_days = timesheets.values('date').distinct().count()
            earnings = working_days * project.rate_value
        else:
            earnings = 0
    elif project.project_type.name.lower() == 'turnkey':
        earnings = project.budget or 0
    else:
        earnings = 0

    profit = earnings - total_expenses - total_da
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
    # fetch timesheets with related slots to reduce queries
    timesheets = Timesheet.objects.filter(project_id=project_id, status='Approved').prefetch_related('time_slots__project', 'employee__user')
    recalculated_claims = []

    for ts in timesheets:
        # group slots by (project_id, slot_date) to produce one DA per day/project
        slot_groups = {}
        for slot in ts.time_slots.all():
            key = (slot.project_id, slot.slot_date)
            slot_groups.setdefault(key, []).append(slot)

        for (proj_id, slot_date), slots in slot_groups.items():
            # use a representative slot for calculate_da which is slot-based
            representative = slots[0]
            try:
                da_amount, currency = calculate_da(representative)
            except Exception:
                # fallback: 0
                da_amount, currency = 0, getattr(representative.project, 'currency', 'INR')
            recalculated_claims.append({
                'employee': ts.employee.user.get_full_name(),
                'date': slot_date,
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