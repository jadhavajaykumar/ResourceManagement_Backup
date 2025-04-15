# timesheet/urls.py
from django.urls import path
from . import views

app_name = 'timesheet'

urlpatterns = [
    path('my-timesheets/', views.my_timesheets, name='my-timesheets'),
    path('approve/<int:timesheet_id>/', views.approve_timesheet, name='approve-timesheet'),
    path('export/csv/', views.export_timesheets_csv, name='export-timesheets-csv'),
]
