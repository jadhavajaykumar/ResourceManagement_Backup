import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from django.utils.timezone import localtime

def export_expenses_to_excel(expenses_queryset):
    data = [{
        "Employee": e.employee.user.get_full_name(),
        "Project": e.project.name if e.project else "",
        "Date": localtime(e.date).strftime("%Y-%m-%d"),
        "Expense Type": e.new_expense_type.name if e.new_expense_type else "",
        "Kilometers": e.kilometers,
        "Amount (₹)": e.amount,
        "Status": e.status,
        "Receipt": e.receipt.url if e.receipt else "",
        "Comments": e.comments or "",
    } for e in expenses_queryset]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Expenses')

    output.seek(0)
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=expenses_export.xlsx'
    return response