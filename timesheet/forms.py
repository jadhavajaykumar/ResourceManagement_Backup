from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Timesheet, TimeSlot
from project.models import Project, Task
from manager.models import TaskAssignment
from datetime import datetime, timedelta
from expenses.models import GlobalExpenseSettings, EmployeeExpenseGrace
from employee.models import EmployeeProfile




class TimeSlotForm(forms.ModelForm):
    class Meta:
        model = TimeSlot
        fields = ['project', 'task', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        if employee:
            # Filter projects and tasks for the employee
            assigned_project_ids = TaskAssignment.objects.filter(
                employee=employee
            ).values_list('project_id', flat=True)
            
            assigned_task_ids = TaskAssignment.objects.filter(
                employee=employee
            ).values_list('task_id', flat=True)
            
            self.fields['project'].queryset = Project.objects.filter(id__in=assigned_project_ids)
            self.fields['task'].queryset = Task.objects.filter(id__in=assigned_task_ids)








class TimesheetForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    shift_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    shift_end = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    is_billable = forms.BooleanField(required=False, initial=True)
    
    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee = employee
        
   


    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        shift_start = cleaned_data.get("shift_start")
        shift_end = cleaned_data.get("shift_end")
        today = timezone.now().date()

        # Step 1: Fetch grace period
        grace_days = 5  # default
        if self.employee:
            # 1. Check for custom grace
            custom_grace = EmployeeExpenseGrace.objects.filter(employee=self.employee).first()
            if custom_grace:
                grace_days = custom_grace.days
            else:
                # 2. Fallback to global grace
                global_grace = GlobalExpenseSettings.objects.first()
                if global_grace:
                    grace_days = global_grace.days

        # Step 2: Validate date against grace
        if date:
            if date > today:
                raise forms.ValidationError("You cannot submit a timesheet for a future date.")
            if date < (today - timedelta(days=grace_days)):
                raise forms.ValidationError(f"You can only submit timesheets within the last {grace_days} days.")

        # Step 3: Shift time logic (including overnight)
        if shift_start and shift_end:
            shift_start_dt = datetime.combine(datetime.today(), shift_start)
            shift_end_dt = datetime.combine(datetime.today(), shift_end)
            if shift_end <= shift_start:
                shift_end_dt += timedelta(days=1)
            total_hours = (shift_end_dt - shift_start_dt).total_seconds() / 3600
            if total_hours <= 0:
                raise forms.ValidationError("Total hours must be greater than 0.")
            cleaned_data["total_hours"] = total_hours

        return cleaned_data
