from django import forms
from .models import DocumentTemplate

class DocumentTemplateForm(forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ['name', 'template_file']



class PDFMergeForm(forms.Form):
    pdf1 = forms.FileField(label="First PDF")
    pdf2 = forms.FileField(label="Second PDF")
    
class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField(label="Upload PDF", help_text="Only PDF files are supported.")
    
from django import forms

class PDFToWordForm(forms.Form):
    pdf_file = forms.FileField(label="Upload PDF", help_text="Only PDF files are supported.")
    