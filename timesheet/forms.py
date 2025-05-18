
from django import forms
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
