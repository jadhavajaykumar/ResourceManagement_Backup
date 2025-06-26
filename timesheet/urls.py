# timesheet/urls.py
from django.urls import path
from . import views
from employee.views.attendance_views import my_c_offs
from .views import apply_c_off
from .views import delete_employee_timesheet_data

app_name = 'timesheet'

urlpatterns = [
    path('my-timesheets/', views.my_timesheets, name='my-timesheets'),
    path('approve/<int:timesheet_id>/', views.approve_timesheet, name='approve-timesheet'),
    path('export/csv/', views.export_timesheets_csv, name='export-timesheets-csv'),
    path('edit/<int:pk>/', views.edit_timesheet, name='edit-timesheet'),
    path('delete/<int:timesheet_id>/', views.delete_timesheet, name='delete-timesheet'),
    #path('delete/<int:pk>/', views.delete_timesheet, name='delete-timesheet'),
    path('c-off/', my_c_offs, name='my-c-offs'),
    path('apply-c-off/', apply_c_off, name='apply-c-off'),
    path('comp-off-approvals/', views.comp_off_approval_view, name='comp-off-approvals'),
    path('resubmit-timesheet/<int:pk>/', views.resubmit_timesheet, name='resubmit-timesheet'),
    path('generate-timeslots/', views.generate_timeslots, name='generate-timeslots'),
    path('submit-timesheet/', views.submit_timesheet, name='submit-timesheet'),
    path('load-tasks/', views.load_tasks_for_employee, name='load-employee-tasks'),
    
    
    #To delete the employee timesheets 
    path('delete-employee-data/<int:employee_id>/', delete_employee_timesheet_data, name='delete-employee-data'),


]
