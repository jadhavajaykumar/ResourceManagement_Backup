import csv
from django.http import HttpResponse
from expenses.models import AdvanceRequest, Expense
from employee.models import EmployeeProfile
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from accountant.views.common import is_accountant

@login_required
@user_passes_test(is_accountant)
def export_advance_expense_summary(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="advance_expense_summary.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Employee', 'Total Advance (₹)', 'Total Expense Used (₹)', 'Remaining/Negative Balance (₹)'
    ])

    employees = EmployeeProfile.objects.all()

    for emp in employees:
        advances = AdvanceRequest.objects.filter(employee=emp, settled_by_account_manager=True)
        expenses = Expense.objects.filter(employee=emp, status='Approved')

        total_advance = advances.aggregate(Sum("amount"))["amount__sum"] or 0
        total_used = expenses.filter(advance_used__in=advances).aggregate(Sum("amount"))["amount__sum"] or 0
        balance = total_advance - total_used

        writer.writerow([
            emp.user.get_full_name(),
            f"{total_advance:.2f}",
            f"{total_used:.2f}",
            f"{balance:.2f}"
        ])

    return response
