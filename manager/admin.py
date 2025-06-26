from django.contrib import admin
from .models import MainSkill, SubSkill
#from employee.models import EmployeeProfile


class SubSkillInline(admin.TabularInline):
    model = SubSkill
    extra = 1

@admin.register(MainSkill)
class MainSkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    inlines = [SubSkillInline]

@admin.register(SubSkill)
class SubSkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'main_skill')
    list_filter = ('main_skill',)

# admin.py
@admin.action(description='Delete all Timesheet + DA + C-Off data')
def delete_timesheet_related_data(modeladmin, request, queryset):
    for employee in queryset:
        Timesheet.objects.filter(employee=employee).delete()
        DailyAllowance.objects.filter(employee=employee).delete()
        CompensatoryOff.objects.filter(employee=employee).delete()
        CompOffBalance.objects.filter(employee=employee).update(balance=0)
    messages.success(request, "Deleted related data for selected employees.")

#@admin.register(EmployeeProfile)
#class EmployeeAdmin(admin.ModelAdmin):
#    list_display = ('user', 'department', 'designation')
#    actions = [delete_timesheet_related_data]
