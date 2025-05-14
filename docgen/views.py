# docgen/views.py
  # Save the new document
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import DocumentTemplate, GeneratedDocument
from .forms import DocumentTemplateForm
from django.http import HttpResponse
from docx import Document as DocxDocument
import re
import os
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from docx.text.run import Run
from django.http import HttpResponse
from openpyxl import load_workbook


def is_manager(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Manager').exists())


@login_required
@user_passes_test(is_manager)
def upload_template(request):
    if request.method == 'POST':
        form = DocumentTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('docgen:list-templates')
    else:
        form = DocumentTemplateForm()
    return render(request, 'docgen/upload_template.html', {'form': form})


@login_required
@user_passes_test(is_manager)
def list_templates(request):
    templates = DocumentTemplate.objects.all()
    return render(request, 'docgen/template_list.html', {'templates': templates})



def extract_placeholders(docx_path):
    doc = DocxDocument(docx_path)
    placeholders = set()

    # Check paragraphs
    for para in doc.paragraphs:
        placeholders.update(re.findall(r'\{\{(.*?)\}\}', para.text))

    # Check tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                placeholders.update(re.findall(r'\{\{(.*?)\}\}', cell.text))

    return sorted(placeholders)





def replace_text_in_runs(runs, replacements):
    for run in runs:
        for key, val in replacements.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in run.text:
                run.text = run.text.replace(placeholder, val)







from django.contrib import messages

@login_required
@user_passes_test(is_manager)
def delete_template(request, template_id):
    template = get_object_or_404(DocumentTemplate, id=template_id)
    if request.method == 'POST':
        template.delete()
        messages.success(request, "Template deleted successfully.")
        return redirect('docgen:list-templates')
    return render(request, 'docgen/confirm_delete.html', {'template': template})
    
def update_excel_file(input_values, excel_path):
    wb = load_workbook(excel_path)
    ws = wb.active
    ws['D4'] = input_values.get('Old_Gross', 0)
    ws['E4'] = input_values.get('New_Gross', 0)
    ws['C1'] = input_values.get('Emp_Id', '')
    ws['C2'] = input_values.get('Emp_Name', '')
    ws['C3'] = input_values.get('Emp_Grade', '')
    wb.save(excel_path)

@login_required
@user_passes_test(is_manager)
def fill_template(request, template_id):
    template = get_object_or_404(DocumentTemplate, id=template_id)
    docx_path = template.template_file.path
    excel_template_path = os.path.join(settings.MEDIA_ROOT, 'excel_templates', 'salary_template.xlsx')

    placeholders = extract_placeholders(docx_path)

    if request.method == 'POST':
        # Dynamic Word placeholders filled from form
        filled_data = {key: request.POST.get(key, '') for key in placeholders}

        # Static Excel-specific fields
        Old_Gross = float(request.POST.get('Old_Gross', 0))
        New_Gross = float(request.POST.get('New_Gross', 0))
        Emp_Id = request.POST.get('Emp_Id', '')
        Emp_Name = request.POST.get('Emp_Name', '')
        Emp_Grade = request.POST.get('Emp_Grade', '')
        

        # Update Excel
        update_excel_file({
            'Old_Gross': Old_Gross,
            'New_Gross': New_Gross,
            'Emp_Id': Emp_Id,
            'Emp_Name': Emp_Name,
            'Emp_Grade': Emp_Grade,
            }, excel_template_path)

        # Replace placeholders in Word (text only)
        doc = DocxDocument(docx_path)
        for paragraph in doc.paragraphs:
            for key, value in filled_data.items():
                paragraph.text = paragraph.text.replace(f"{{{{{key}}}}}", value)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, value in filled_data.items():
                        cell.text = cell.text.replace(f"{{{{{key}}}}}", value)

        # Save the document
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        filename = f"{template.name.replace(' ', '_')}_{timestamp}_filled.docx"
        output_path = os.path.join(settings.MEDIA_ROOT, 'generated_docs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)

        GeneratedDocument.objects.create(
            template=template,
            filled_data=filled_data,
            generated_docx=f'generated_docs/{filename}'
        )

        return HttpResponse(f"""
            <div style='padding:20px; font-family:Arial;'>
                <h3>Document generated successfully: {filename}</h3>
                <p><a href='/media/generated_docs/{filename}' target='_blank'>📄 Download Word File</a></p>
            </div>
        """)

    return render(request, 'docgen/fill_template.html', {
        'template': template,
        'placeholders': placeholders,
    })   
