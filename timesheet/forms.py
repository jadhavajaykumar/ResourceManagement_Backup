

from django import forms
from .models import Timesheet

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
