from django.shortcuts import render
from project.services.reporting_service import (
    get_project_profitability,
    get_employee_da_claims,
    get_timesheet_earning_report,
)
from project.services.export_helpers import (
    export_project_profitability_excel,
    export_da_claims_excel,
    export_timesheet_earnings_excel,
    export_project_profitability_pdf,
)

def project_profitability_view(request, project_id):
    data = get_project_profitability(project_id)
    return render(request, 'project/profitability.html', {'data': data})

def project_da_claims_view(request, project_id):
    claims = get_employee_da_claims(project_id)
    return render(request, 'project/da_claims.html', {'claims': claims})

def project_timesheet_earning_report_view(request, project_id):
    report = get_timesheet_earning_report(project_id)
    return render(request, 'project/earning_report.html', {'report': report})

# Export endpoints are now handled by service wrappers
def export_project_profitability_excel_view(request, project_id):
    return export_project_profitability_excel(project_id)

def export_da_claims_excel_view(request, project_id):
    return export_da_claims_excel(project_id)

def export_timesheet_earnings_excel_view(request, project_id):
    return export_timesheet_earnings_excel(project_id)

def export_project_profitability_pdf_view(request, project_id):
    return export_project_profitability_pdf(project_id)