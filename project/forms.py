# project/forms.py

import pycountry
from django import forms
from .models import Project, Task, Subtask

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'customer_name', 'description', 'project_type', 'billing_method',
            'budget', 'daily_hourly_rate', 'location', 'country', 'currency', 
            'da_rate_per_hour', 'extra_hour_rate', 'start_date', 'end_date', 'status', 'documents'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['project', 'name', 'description', 'due_date', 'progress']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class SubtaskForm(forms.ModelForm):
    class Meta:
        model = Subtask
        fields = ['task', 'name', 'completed']




# Currency dropdown options
CURRENCY_CHOICES = [(c.alpha_3, f"{c.name} ({c.alpha_3})") for c in pycountry.currencies]

class ProjectForm(forms.ModelForm):
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES, required=False)

    class Meta:
        model = Project
        fields = '__all__'

