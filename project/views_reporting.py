from django.shortcuts import render
from .services_reporting import get_project_profitability, get_employee_da_claims, get_timesheet_earning_report

def project_profitability_view(request, project_id):
    data = get_project_profitability(project_id)
    return render(request, 'project/profitability.html', {'data': data})

def project_da_claims_view(request, project_id):
    claims = get_employee_da_claims(project_id)
    return render(request, 'project/da_claims.html', {'claims': claims})

def project_timesheet_earning_report_view(request, project_id):
    report = get_timesheet_earning_report(project_id)
    return render(request, 'project/earning_report.html', {'report': report})


from .services_reporting import get_project_profitability, get_employee_da_claims, get_timesheet_earning_report
from .services.export_service import export_to_excel, export_to_pdf

def export_project_profitability_excel(request, project_id):
    data = get_project_profitability(project_id)
    report_data = [data]
    columns = ['project_name', 'total_earnings', 'total_expenses', 'total_da_claimed', 'net_profit', 'expense_percentage', 'profit_percentage']
    return export_to_excel(report_data, columns, filename='Project_Profitability.xlsx')

def export_da_claims_excel(request, project_id):
    data = get_employee_da_claims(project_id)
    columns = ['employee__user__first_name', 'employee__user__last_name', 'total_da', 'entries']
    return export_to_excel(data, columns, filename='DA_Claims.xlsx')

def export_timesheet_earnings_excel(request, project_id):
    data = get_timesheet_earning_report(project_id)
    columns = ['employee', 'date', 'hours', 'earning', 'da_claimed']
    return export_to_excel(data, columns, filename='Timesheet_Earnings.xlsx')

def export_project_profitability_pdf(request, project_id):
    data = [get_project_profitability(project_id)]
    columns = ['project_name', 'total_earnings', 'total_expenses', 'total_da_claimed', 'net_profit', 'expense_percentage', 'profit_percentage']
    return export_to_pdf(data, columns, filename='Project_Profitability.pdf')
