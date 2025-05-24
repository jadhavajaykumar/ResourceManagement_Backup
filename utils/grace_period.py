# utils/grace_period.py
from datetime import date, timedelta
from expenses.models import GlobalExpenseSettings, EmployeeExpenseGrace



def get_allowed_grace_days(employee):
    custom = EmployeeExpenseGrace.objects.filter(employee=employee).first()
    if custom:
        return custom.days
    global_setting = GlobalExpenseSettings.objects.first()
    return global_setting.days if global_setting else 5

def is_within_grace(submitted_date, allowed_days):
    today = date.today()
    return submitted_date >= today - timedelta(days=allowed_days)

def validate_grace_period(employee, submitted_date):
    allowed_days = get_allowed_grace_days(employee)
    return is_within_grace(submitted_date, allowed_days), allowed_days
