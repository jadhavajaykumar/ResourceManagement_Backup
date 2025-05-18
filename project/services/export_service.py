import openpyxl
from openpyxl.utils import get_column_letter
from django.http import HttpResponse

def export_to_excel(report_data, columns, filename='report.xlsx'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Report'

    # Write headers
    for col_num, column_title in enumerate(columns, 1):
        ws[f'{get_column_letter(col_num)}1'] = column_title

    # Write data rows
    for row_num, row_data in enumerate(report_data, 2):
        for col_num, key in enumerate(columns, 1):
            ws[f'{get_column_letter(col_num)}{row_num}'] = row_data.get(key, '')

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse

def export_to_pdf(report_data, columns, filename='report.pdf'):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    style_sheet = getSampleStyleSheet()
    elements.append(Paragraph('Report', style_sheet['Title']))

    table_data = [columns] + [
        [str(row.get(col, '')) for col in columns] for row in report_data
    ]

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(table)

    doc.build(elements)
    return response
