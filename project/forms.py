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
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

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

    def __init__(self, *args, **kwargs):
        project_type = kwargs.pop("project_type", None)
        super().__init__(*args, **kwargs)
        
        project_type = project_type or getattr(self.instance, "project_type", None)
        project_type_name = project_type.name.lower() if project_type else ""
        location = getattr(self.instance, "location_type", None)
        location_name = location.name.lower() if location else ""
        
        for field in self.fields.values():
            existing_classes = field.widget.attrs.get('class', '')
            classes = existing_classes.split()
            if 'form-control' not in classes:
                classes.append('form-control')
            field.widget.attrs['class'] = ' '.join(classes)
            
    
    def clean(self):
        cleaned_data = super().clean()

        project_type = cleaned_data.get('project_type')
        project_type_name = project_type.name.lower() if project_type else ''

        location_type = cleaned_data.get('location_type')
        location_name = location_type.name.lower() if location_type else ''
        
        if project_type_name == 'service':
            self.fields['rate_type'].required = True
            self.fields['rate_value'].required = True
        elif project_type_name == 'turnkey':
            self.fields['budget'].required = True

        if location_name in ['local', 'domestic', 'international']:
            self.fields['da_rate_per_unit'].required = True

        if location_name == 'international':
            self.fields['da_type'].required = True
            self.fields['extended_hours_threshold'].required = True
            self.fields['extended_hours_da_rate'].required = True
            self.fields['off_day_da_rate'].required = True



