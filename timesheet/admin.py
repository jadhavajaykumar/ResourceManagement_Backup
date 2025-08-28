from django.contrib import admin
from timesheet.models import Timesheet

@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "date", "status")  # adjust to your fields
    search_fields = ("employee__user__first_name", "employee__user__last_name")
    list_filter = ("date", "status")
