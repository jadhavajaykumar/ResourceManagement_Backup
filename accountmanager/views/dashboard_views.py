# Views for Account Manager dashboard
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum
#from datetime import datetime
from employee.models import EmployeeProfile
import re
#from accountmanager.utils import is_accountmanager
from expenses.models import Expense, DailyAllowance, AdvanceRequest
from utils.currency import format_currency
from django.contrib import messages
from collections import defaultdict
from django.urls import reverse
from django.db.models import Q
from django.utils.dateparse import parse_date
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import date
from django.contrib.auth.decorators import login_required, permission_required
import io
import xlsxwriter
from django.http import HttpResponse
from django.contrib.auth import get_user_model


@login_required
@permission_required('expenses.can_settle')
def export_settlement_summary_excel(request):
    User = get_user_model()

    expense_totals = Expense.objects.filter(
        status="Approved", reimbursed=False, forwarded_to_accountmanager=True
    ).values('employee', 'currency').annotate(total=Sum('amount'))

    da_totals = DailyAllowance.objects.filter(
        approved=True, reimbursed=False, forwarded_to_accountmanager=True
    ).values('employee', 'currency').annotate(total=Sum('da_amount'))

    # Group totals by employee and currency
    totals = {}
    for e in expense_totals:
        key = (e['employee'], e['currency'])
        totals[key] = totals.get(key, 0) + e['total']
    for d in da_totals:
        key = (d['employee'], d['currency'])
        totals[key] = totals.get(key, 0) + d['total']

    employee_map = {u.id: u.get_full_name() for u in User.objects.filter(id__in={k[0] for k in totals})}

    # Prepare Excel file
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    currency_format = workbook.add_format({'num_format': '#,##0.00'})

    # Write headers
    headers = ['Employee Name', 'Currency', 'Total Unsettled Amount']
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header, header_format)

    # Write data rows
    for row_num, ((emp_id, currency), total) in enumerate(totals.items(), start=1):
        worksheet.write(row_num, 0, employee_map.get(emp_id, ''))
        worksheet.write(row_num, 1, currency)
        worksheet.write_number(row_num, 2, float(total), currency_format)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="settlement_summary.xlsx"'
    return response


@login_required
@permission_required('expenses.can_settle')
def dashboard_view(request):
    profile = EmployeeProfile.objects.get(user=request.user)
    return render(request, 'accountmanager/dashboard.html', {'profile': profile})

@login_required
@permission_required('expenses.can_settle')
def reimbursement_dashboard(request):
    # Tab 1: Pending Reimbursement – Manager Approved
    expenses = Expense.objects.filter(
        status="Forwarded to Account Manager",
        reimbursed=False,
        forwarded_to_accountmanager=True
    ).select_related('employee__user', 'project')

    allowances = DailyAllowance.objects.filter(
        approved=True,
        reimbursed=False,
        forwarded_to_accountmanager=True
    ).select_related('employee__user', 'project')

    reimbursement_entries = []

    # Add expenses
    for expense in expenses:
        reimbursement_entries.append({
            "type": "Expense",
            "employee": expense.employee,
            "employee_name": expense.employee.user.get_full_name(),
            "project": expense.project,
            "amount": format_currency(expense.amount, getattr(expense, 'currency', 'INR')),
            "date": expense.date,
        settled_by_account_manager=False
    ).select_related('employee__user', 'project')

    return render(request, 'accountmanager/reimbursement_dashboard.html', {
        'reimbursement_entries': reimbursement_entries,
        'employee_summaries': grouped_summary,
        'settled_data': settled_data,
        'settled_merged': settled_merged,
        'employee_map': employee_map,
        'tab_data': {
            'advances': approved_advances
        },
        'active_tab': request.GET.get("tab", "tab1"),
    })










@login_required
@permission_required('expenses.can_settle')
def settlement_summary(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    expense_totals = Expense.objects.filter(
        status="Approved", reimbursed=False, forwarded_to_AccountManager=True
    ).values('employee', 'currency').annotate(total=Sum('amount'))

    da_totals = DailyAllowance.objects.filter(
        approved=True, reimbursed=False, forwarded_to_AccountManager=True
    ).values('employee', 'currency').annotate(total=Sum('da_amount'))

    # Group by employee and currency
    totals = {}
    for e in expense_totals:
        key = (e['employee'], e['currency'])
        totals[key] = totals.get(key, 0) + e['total']
    for d in da_totals:
        key = (d['employee'], d['currency'])
        totals[key] = totals.get(key, 0) + d['total']

    employee_map = {u.id: u.get_full_name() for u in User.objects.filter(id__in={k[0] for k in totals})}
    final_data = [
        {
            'employee_id': emp_id,
            'employee': employee_map.get(emp_id, ''),
            'total': total,
            'currency': currency
        }
        for (emp_id, currency), total in totals.items()
    ]

    return render(request, 'accountmanager/settlement_summary.html', {
        'totals': final_data,
        'format_currency': format_currency,
    })


@login_required
@permission_required('expenses.can_settle')
def settle_employee(request, employee_id):
    if request.method == "POST":
        Expense.objects.filter(employee_id=employee_id, status="Approved", reimbursed=False, forwarded_to_AccountManager=True).update(
            reimbursed=True
        )
        DailyAllowance.objects.filter(employee_id=employee_id, approved=True, reimbursed=False, forwarded_to_AccountManager=True).update(
            reimbursed=True
        )
        return redirect('accountmanager:settlement-summary')
    return redirect('accountmanager:settlement-summary')


@login_required
@permission_required('expenses.can_settle')
def settle_selected(request):
    if request.method == "POST":
        employee_id = request.POST.get("settle_employee")
        reimbursement_date = request.POST.get(f"settlement_date_{employee_id}")

        if not employee_id:
            messages.error(request, "No employee selected for reimbursement.")
            return redirect(f"{reverse('accountmanager:reimbursement_dashboard')}?tab=tab2")

        if not reimbursement_date:
            messages.error(request, "Please enter a settlement date.")
            return redirect(f"{reverse('accountmanager:reimbursement_dashboard')}?tab=tab2")

        # Mark expenses & DA as reimbursed
        Expense.objects.filter(
            employee_id=employee_id,
            status="Forwarded to Account Manager",
            reimbursed=False,
            forwarded_to_accountmanager=True
        ).update(
            reimbursed=True,
            status="Approved",
            settlement_date=reimbursement_date
        )