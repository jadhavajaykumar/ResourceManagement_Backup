from django.urls import path
from . import views

app_name = 'project'

urlpatterns = [
    path('', views.project_dashboard, name='project-dashboard'),
    path('edit-task/<int:task_id>/', views.edit_task, name='edit-task'),
    path('delete-project/<int:project_id>/', views.delete_project, name='delete-project'),
    path('delete-task/<int:task_id>/', views.delete_task, name='delete-task'),
    path('ajax/get-country-rates/', views.get_country_rates, name='get-country-rates'),
    path('edit-project/<int:project_id>/', views.edit_project, name='edit-project'),


]
