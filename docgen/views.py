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





@login_required
@user_passes_test(is_manager)
def fill_template(request, template_id):
    template = get_object_or_404(DocumentTemplate, id=template_id)
    docx_path = template.template_file.path
    placeholders = extract_placeholders(docx_path)

    if request.method == 'POST':
        filled_data = {key: request.POST.get(key, '') for key in placeholders}
        doc = DocxDocument(docx_path)

        # Replace placeholders in paragraphs
        for paragraph in doc.paragraphs:
            for key, value in filled_data.items():
                paragraph.text = paragraph.text.replace(f"{{{{{key}}}}}", value)

        # Replace placeholders in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, value in filled_data.items():
                        cell.text = cell.text.replace(f"{{{{{key}}}}}", value)

        # Save the new document with timestamp
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        filename = f"{template.name.replace(' ', '_')}_{timestamp}_filled.docx"
        output_dir = os.path.join(settings.MEDIA_ROOT, 'generated_docs')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
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
                <a href="{reverse('docgen:list-templates')}" class="btn btn-secondary mt-2">Back to Templates</a>
            </div>
        """)

    return render(request, 'docgen/fill_template.html', {
        'template': template,
        'placeholders': placeholders,
    })

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
