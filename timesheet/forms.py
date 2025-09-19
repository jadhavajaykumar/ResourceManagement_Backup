from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Timesheet, TimeSlot
from project.models import Project, Task
try:
    from skills.models import TaskAssignment
except ImportError:  # Skills app may not be installed
    TaskAssignment = None
from datetime import datetime, timedelta
from expenses.models import GlobalExpenseSettings, EmployeeExpenseGrace
from employee.models import EmployeeProfile

def _coerce_worked_onsite(value):
    if value in (True, "True", "true", "1", 1):
        return True
    if value in (False, "False", "false", "0", 0):
        return False
    return None


class TimeSlotForm(forms.ModelForm):
    worked_onsite = forms.TypedChoiceField(
        label="Worked onsite?",
        choices=(
            ("", "Use project default"),
            ("True", "Onsite"),
            ("False", "Office"),
        ),
        required=False,
        coerce=_coerce_worked_onsite,
        empty_value=None,
    )
    
    class Meta:
        model = TimeSlot
        fields = ['project', 'task', 'description', 'time_from', 'time_to', 'worked_onsite']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'time_from': forms.TimeInput(attrs={'type': 'time'}),
            'time_to': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            value = self.instance.worked_onsite
            if value is True:
                self.initial['worked_onsite'] = 'True'
            elif value is False:
                self.initial['worked_onsite'] = 'False'

        self.fields['worked_onsite'].widget.attrs.update({'class': 'form-select'})

        if employee and TaskAssignment:
            assigned_project_ids = TaskAssignment.objects.filter(
                employee=employee
            ).values_list('project_id', flat=True)

            assigned_task_ids = TaskAssignment.objects.filter(
                employee=employee
            ).values_list('task_id', flat=True)

            self.fields['project'].queryset = Project.objects.filter(id__in=assigned_project_ids)
            self.fields['task'].queryset = Task.objects.filter(id__in=assigned_task_ids)

    def clean(self):
        cleaned_data = super().clean()
        time_from = cleaned_data.get('time_from')
        time_to = cleaned_data.get('time_to')

        if time_from and time_to:
            if time_to <= time_from:
                raise forms.ValidationError("End time must be after start time.")
        return cleaned_data






class TimesheetForm(forms.ModelForm):
    class Meta:
        model = Timesheet
        fields = ['date', 'shift_start', 'shift_end', 'is_billable']

        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'shift_start': forms.TimeInput(attrs={'type': 'time'}),
            'shift_end': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, employee=None, **kwargs):
        self.employee = employee
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        shift_start = cleaned_data.get("shift_start")
        shift_end = cleaned_data.get("shift_end")
        today = timezone.now().date()

        grace_days = 5
        if self.employee:
            custom_grace = EmployeeExpenseGrace.objects.filter(employee=self.employee).first()
            if custom_grace:
                grace_days = custom_grace.days
            else:
                global_grace = GlobalExpenseSettings.objects.first()
                if global_grace:
                    grace_days = global_grace.days

        if date:
            if date > today:
                raise forms.ValidationError("You cannot submit a timesheet for a future date.")
            if date < (today - timedelta(days=grace_days)):
                raise forms.ValidationError(f"You can only submit timesheets within the last {grace_days} days.")

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

