from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Timesheet
from project.models import Project, Task
from manager.models import TaskAssignment

class TimesheetForm(forms.ModelForm):
    class Meta:
        model = Timesheet
        fields = ['project', 'task', 'date', 'time_from', 'time_to', 'task_description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time_from': forms.TimeInput(attrs={'type': 'time'}),
            'time_to': forms.TimeInput(attrs={'type': 'time'}),
            'task_description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)

        if employee:
            assigned_project_ids = TaskAssignment.objects.filter(employee=employee).values_list('project_id', flat=True)
            assigned_task_ids = TaskAssignment.objects.filter(employee=employee).values_list('task_id', flat=True)

            self.fields['project'].queryset = Project.objects.filter(id__in=assigned_project_ids)
            self.fields['task'].queryset = Task.objects.filter(id__in=assigned_task_ids)

    def clean_date(self):
        date = self.cleaned_data['date']
        if date > timezone.now().date():
            raise ValidationError("You cannot submit timesheets for future dates.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        time_from = cleaned_data.get('time_from')
        time_to = cleaned_data.get('time_to')
        
        if time_from and time_to and time_from >= time_to:
            raise ValidationError("End time must be after start time.")
        
        return cleaned_data