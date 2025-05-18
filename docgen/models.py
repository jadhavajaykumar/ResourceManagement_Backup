from django.db import models

class DocumentTemplate(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_file = models.FileField(upload_to='doc_templates/')

    def __str__(self):
        return self.name

class GeneratedDocument(models.Model):
    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE)
    filled_data = models.JSONField()
    generated_docx = models.FileField(upload_to='generated_docs/', null=True, blank=True)
    generated_pdf = models.FileField(upload_to='generated_pdfs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
