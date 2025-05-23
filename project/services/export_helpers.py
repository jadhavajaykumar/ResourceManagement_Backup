from project.services.reporting_service import (
    get_project_profitability,
    get_employee_da_claims,
    get_timesheet_earning_report,
)
from project.services.export_service import export_to_excel, export_to_pdf

def export_project_profitability_excel(request, project_id):
    data = get_project_profitability(project_id)
    report_data = [data]
    columns = ['project_name', 'total_earnings', 'total_expenses', 'total_da_claimed', 'net_profit', 'expense_percentage', 'profit_percentage']
    return export_to_excel(report_data, columns, filename='Project_Profitability.xlsx')

def export_da_claims_excel(request, project_id):
    data = get_employee_da_claims(project_id)
    columns = ['employee', 'date', 'calculated_da', 'currency']
    return export_to_excel(data, columns, filename='DA_Claims.xlsx')

def export_timesheet_earnings_excel(request, project_id):
    data = get_timesheet_earning_report(project_id)
    columns = ['employee', 'date', 'hours', 'earning', 'da_claimed']
    return export_to_excel(data, columns, filename='Timesheet_Earnings.xlsx')

def export_project_profitability_pdf(request, project_id):
    data = [get_project_profitability(project_id)]
    columns = ['project_name', 'total_earnings', 'total_expenses', 'total_da_claimed', 'net_profit', 'expense_percentage', 'profit_percentage']
    return export_to_pdf(data, columns, filename='Project_Profitability.pdf')