# Views for Account Manager dashboard
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from datetime import datetime
from accounts.utils import is_accountmanager
from employee.models import EmployeeProfile
import re
#from accountmanager.utils import is_accountmanager
from expenses.models import Expense, DailyAllowance
from utils.currency import format_currency
from django.contrib import messages
from collections import defaultdict

from django.urls import reverse
from django.db.models import Q
from django.utils.dateparse import parse_date


 # Adjust path as needed




from accountmanager.views.common import is_accountmanager  # ensure this role check exists



import io
import xlsxwriter
from django.http import HttpResponse

from django.contrib.auth import get_user_model


@login_required
@user_passes_test(is_accountmanager)
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
    worksheet = workbook.add_worksheet('Settlement Summary')

    header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2'})
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
@user_passes_test(is_accountmanager)
def dashboard_view(request):
    profile = EmployeeProfile.objects.get(user=request.user)
    return render(request, 'accountmanager/dashboard.html', {'profile': profile})





# accountmanager/views/dashboard_views.py




@login_required
@user_passes_test(is_accountmanager)
def reimbursement_dashboard(request):
    # Get all approved but unreimbursed expenses and DA

    expenses = Expense.objects.select_related('employee__user', 'project').filter(status="Approved", reimbursed=False)
    allowances = DailyAllowance.objects.select_related('employee__user', 'project').filter(approved=True, reimbursed=False)

    # Tab 1: Individual Entries (Unreimbursed)
    reimbursement_entries = []
    for expense in expenses:
        #employee_name = expense.employee.user.get_full_name()
        #print("Expense employee:", expense.employee.user.get_full_name())
        #print("Expense:", expense.id, "| Employee Name:", employee_name)
        reimbursement_entries.append({
            #"employee_name": expense.employee.get_full_name() if hasattr(expense.employee, 'get_full_name') else str(expense.employee),
            #"employee_name": expense.employee.user.get_full_name(),  # Corrected here
            "employee_name": expense.employee.user.get_full_name(),
            #"employee_name": employee_name,
            "type": "Expense",
            "employee": expense.employee,
            "project": expense.project,
            "amount": format_currency(expense.amount, getattr(expense, 'currency', 'INR')),
            "date": expense.date,
            "expense_type": expense.new_expense_type,
            "id": expense.id,
        })

    for da in allowances:
        #employee_name = da.employee.user.get_full_name()
        #print("DA:", da.id, "| Employee Name:", employee_name)
        reimbursement_entries.append({
            #"employee_name": da.employee.get_full_name() if hasattr(da.employee, 'get_full_name') else str(da.employee),
            "employee_name": da.employee.user.get_full_name(),
            "type": "DA",
            "employee": da.employee,
            "project": da.project,
            "amount": format_currency(da.da_amount, da.currency),
            "date": da.date,
            "expense_type": "DA",
            "id": da.id,
        })

    # Tab 2: Grouped by Employee
    employee_summaries = {}
    for entry in reimbursement_entries:
        emp = entry["employee"]
        emp_id = emp.id
        amt_str = entry["amount"]
        symbol = amt_str[0]
        amt = float(amt_str[1:].replace(',', '').strip())

        if emp_id not in employee_summaries:
            employee_summaries[emp_id] = {
                "employee": emp,
                "total_amount": 0.0,
                "currency_symbol": symbol,
            }
        employee_summaries[emp_id]["total_amount"] += amt

    # Convert to list and format total
    grouped_summary = []
    for summary in employee_summaries.values():
        total_amt = summary["total_amount"]
        summary["total_formatted"] = f"{summary['currency_symbol']} {total_amt:,.2f}"
        grouped_summary.append(summary)

    # Tab 3: Settled
    #settled_expenses = Expense.objects.select_related('employee', 'project').filter(status="Approved", reimbursed=True)
    #settled_allowances = DailyAllowance.objects.select_related('employee', 'project').filter(approved=True, reimbursed=True)
    # Collect all employee IDs from settled data
    

    

    
    # Tab 3: Settled
    settled_expenses = Expense.objects.select_related('employee__user', 'project').filter(status="Approved", reimbursed=True)
    settled_das = DailyAllowance.objects.select_related('employee__user', 'project').filter(approved=True, reimbursed=True)

    # Build settled_data first
    settled_data = defaultdict(list)
    for e in settled_expenses:
        emp = e.employee
        if emp:
            settled_data[emp.id].append({
                "type": "Expense",
                "employee": emp,
                "project": e.project,
                "amount": format_currency(e.amount, getattr(e, 'currency', 'INR')),
                "date": e.date,
            })

    for d in settled_das:
        emp = d.employee
        if emp:
            settled_data[emp.id].append({
                "type": "DA",
                "employee": emp,
                "project": d.project,
                "amount": format_currency(d.da_amount, d.currency),
                "date": d.date,
            })

    # Now safely access settled_data keys
    settled_employee_ids = list(settled_data.keys())

    # Build employee_map only for valid IDs
    employee_qs = EmployeeProfile.objects.select_related('user').filter(id__in=settled_employee_ids)
    employee_map = {emp.id: emp for emp in employee_qs}

    # Remove entries with missing employee_map data
    settled_data = {
        emp_id: entries
        for emp_id, entries in settled_data.items()
        if emp_id in employee_map
    }

        
    #employee_map[emp.id] = emp   
    # Build employee_map for all relevant employees
    print("Settled Employees Loaded:", list(employee_map.keys()))
    print("Final Settled Data Keys (filtered):", list(settled_data.keys()))

    
    print("Settled data keys (employee IDs):", list(settled_data.keys()))
    print("Employee map keys:", list(employee_map.keys()))

    return render(request, 'accountmanager/reimbursement_dashboard.html', {
        'reimbursement_entries': reimbursement_entries,
        'employee_summaries': grouped_summary,
        'settled_data': settled_data,
        'employee_map': employee_map,
    })








@login_required
@user_passes_test(is_accountmanager)
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
@user_passes_test(is_accountmanager)
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
@user_passes_test(is_accountmanager)
def settle_selected(request):
    if request.method == "POST":
        employee_id = request.POST.get("settle_employee")
        if not employee_id:
            messages.error(request, "No employee selected for reimbursement.")
            return redirect(f"{reverse('accountmanager:reimbursement_dashboard')}?tab=tab2")

        date_field = f"settlement_date_{employee_id}"
        reimbursement_date = request.POST.get(date_field)

        if not reimbursement_date:
            messages.error(request, "Please enter a reimbursement date.")
            return redirect(f"{reverse('accountmanager:reimbursement_dashboard')}?tab=tab2")

        # Parse and validate the date
        try:
            date_obj = parse_date(reimbursement_date)
            if not date_obj:
                raise ValueError
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect(f"{reverse('accountmanager:reimbursement_dashboard')}?tab=tab2")

        # Mark reimbursements as settled
        Expense.objects.filter(
            employee__id=employee_id, status="Approved", reimbursed=False
        ).update(reimbursed=True)

        DailyAllowance.objects.filter(
            employee__id=employee_id, approved=True, reimbursed=False
        ).update(reimbursed=True)

        messages.success(request, "Reimbursement marked as settled.")
        return redirect('accountmanager:reimbursement_dashboard')

