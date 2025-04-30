from django import forms
from .models import Project, Task, Subtask, CountryDARate
import pycountry

CURRENCY_CHOICES = [(c.alpha_3, f"{c.name} ({c.alpha_3})") for c in pycountry.currencies]

BILLING_CHOICES = [
    ('Daily', 'Man Day Basis'),
    ('Hourly', 'Man Hour Basis'),
]

class ProjectForm(forms.ModelForm):
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES, required=False)
    billing_method = forms.ChoiceField(choices=BILLING_CHOICES, required=False)

    class Meta:
        model = Project
        fields = [
            'name', 'customer_name', 'description', 'location', 'project_type',
            'currency', 'budget', 'billing_method',
            'start_date', 'end_date', 'status', 'documents'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['project', 'name', 'description', 'due_date', 'progress']
        widgets = {'due_date': forms.DateInput(attrs={'type': 'date'})}

class SubtaskForm(forms.ModelForm):
    class Meta:
        model = Subtask
        fields = ['task', 'name', 'completed']

class CountryRateForm(forms.ModelForm):
    class Meta:
        model = CountryDARate
        fields = ['country', 'currency', 'da_rate_per_hour', 'extra_hour_rate']
