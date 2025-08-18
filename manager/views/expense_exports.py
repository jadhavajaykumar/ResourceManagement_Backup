from django.http import HttpResponse
import pandas as pd
import xlsxwriter
from io import BytesIO
from expenses.models import Expense

def export_manager_expenses(request):
    # Filter manager-visible expenses
    expenses = Expense.objects.select_related('employee__user', 'project', 'new_expense_type')\
                .filter(status='Approved')  # or use dynamic filters

    data = []
    for exp in expenses:
        data.append({
            "Date": exp.date.strftime("%Y-%m-%d"),
            "Employee": exp.employee.user.get_full_name(),
            "Project": exp.project.name if exp.project else "-",
            "Type": exp.new_expense_type.name if exp.new_expense_type else "-",
            "From Location": exp.from_location or "",
            "To Location": exp.to_location or "",
            "Amount": exp.amount,
            "Status": exp.status,
        })

    df = pd.DataFrame(data)
    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Manager Expenses')
        workbook = writer.book
        worksheet = writer.sheets['Manager Expenses']

        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
        for col_num, value in enumerate(df.columns):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)

    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=manager_expenses.xlsx'
    return response
