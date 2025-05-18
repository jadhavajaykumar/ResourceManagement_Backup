from django import forms
from .models import Project, Task, Subtask
from expenses.models import CountryDARate
import pycountry
from django import forms
from .models import Project

CURRENCY_CHOICES = [(c.alpha_3, f"{c.name} ({c.alpha_3})") for c in pycountry.currencies]

BILLING_CHOICES = [
    ('Daily', 'Man Day Basis'),
    ('Hourly', 'Man Hour Basis'),
]



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


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        location = cleaned_data.get('location_type')
        if location and location.name.lower() == 'international':
            if not cleaned_data.get('da_rate_per_day'):
                self.add_error('da_rate_per_day', 'DA rate per day is required for International projects.')
            if not cleaned_data.get('extended_hours_threshold'):
                self.add_error('extended_hours_threshold', 'Extended hours threshold is required for International projects.')
            if not cleaned_data.get('extended_hours_da_rate'):
                self.add_error('extended_hours_da_rate', 'Extended hours DA rate is required for International projects.')
        return cleaned_data

