# docgen/urls.py

from django.urls import path
from . import views
from .views import combined_pdf_tools_view

app_name = 'docgen'

urlpatterns = [
    path('upload/', views.upload_template, name='upload-template'),
    path('templates/', views.list_templates, name='list-templates'),
    path('fill/<int:template_id>/', views.fill_template, name='fill-template'),
    path('delete/<int:template_id>/', views.delete_template, name='delete-template'),
    #path('merge-pdfs/', views.merge_pdfs_view, name='merge_pdfs'),
    path('pdf-tools/', combined_pdf_tools_view, name='combined-pdf-tools'),
   

]



