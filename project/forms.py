from django import forms
from expenses.models import CountryDARate
import pycountry
from .models import Project, LocationType, ProjectType, ProjectStatus, Task, Subtask


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
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Project
        fields = '__all__'
        labels = {
            'rate_value': 'Customer Billing Rate',
            'daily_rate': 'Employee Daily Rate',
            'da_rate_per_unit': 'DA Rate (per Hour/Day)',
            'extended_hours_da_rate': 'Extra Hours DA Rate',
            'extended_hours_threshold': 'Extra Hours Threshold (Weekly)',
            'off_day_da_rate': 'Weekend Off-Day DA',
         }
        help_texts = {
            'rate_type': 'Choose how you will bill the customer – per hour or per day.',
            'rate_value': 'Enter the rate you are charging the customer based on the selected rate type.',
            'da_type': 'Select if DA should be paid daily or hourly for international projects.',
            'da_rate_per_unit': 'DA amount for Local, Domestic, or International projects.',
            'extended_hours_threshold': 'Hours above which extra DA is paid weekly. (e.g. 50 hrs)',
            'extended_hours_da_rate': 'DA rate for the hours worked above threshold.',
            'off_day_da_rate': 'Fixed DA for off-days (weekends) in international projects.',
            'budget': 'Total project budget for Turnkey projects.',
            'daily_rate': 'Standard daily charge for Service-based projects.',
         }

    def clean(self):
        cleaned_data = super().clean()
        project_type = cleaned_data.get('project_type')
        location = cleaned_data.get('location_type')

        project_type_name = project_type.name.lower() if project_type else ""
        location_name = location.name.lower() if location else ""

        if project_type_name == 'service':
            if not cleaned_data.get('rate_type'):
                self.add_error('rate_type', 'Billing method is required for service projects.')
            if not cleaned_data.get('rate_value'):
                self.add_error('rate_value', 'Rate value is required for service projects.')

        if project_type_name == 'turnkey':
            if not cleaned_data.get('budget'):
                self.add_error('budget', 'Budget is required for Turnkey projects.')

        if location_name in ['local', 'domestic', 'international']:
            if not cleaned_data.get('da_rate_per_unit'):
                self.add_error('da_rate_per_unit', 'DA rate per day is required.')

        if location_name == 'international':
            if not cleaned_data.get('da_type'):
                self.add_error('da_type', 'DA type is required for international projects.')
            if not cleaned_data.get('extended_hours_threshold'):
                self.add_error('extended_hours_threshold', 'Threshold is required for extra hours DA.')
            if not cleaned_data.get('extended_hours_da_rate'):
                self.add_error('extended_hours_da_rate', 'Extra hours DA rate is required.')
            if not cleaned_data.get('off_day_da_rate'):
                self.add_error('off_day_da_rate', 'Off-day DA is required for international projects.')

        return cleaned_data



