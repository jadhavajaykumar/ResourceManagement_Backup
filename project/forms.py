from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from expenses.models import CountryDARate
import pycountry
from skills.models import TaskAssignment
from .models import Project, LocationType, ProjectType, ProjectStatus, Task, Subtask, ProjectMaterial

from django.core.exceptions import ValidationError


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


class TaskAssignmentForm(forms.ModelForm):
    class Meta:
        model = TaskAssignment
        fields = ['employee', 'project', 'task']
        
class CountryRateForm(forms.ModelForm):
    class Meta:
        model = CountryDARate
        fields = ['country', 'currency', 'da_rate_per_hour', 'extra_hour_rate']


class ProjectMaterialForm(forms.ModelForm):
    class Meta:
        model = ProjectMaterial
        fields = ['name', 'make', 'quantity', 'price']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow all fields to be optional so an empty inline form can be ignored.
        optional_fields = ['name', 'make', 'quantity', 'price']
        for optional_field in optional_fields:
            field = self.fields[optional_field]
            field.required = False
            if optional_field in {'quantity', 'price'}:
                field.initial = None
            
        
        for field in self.fields.values():
            existing_classes = field.widget.attrs.get('class', '')
            classes = existing_classes.split()
            if 'form-control' not in classes:
                classes.append('form-control')
            field.widget.attrs['class'] = ' '.join(classes)
    def clean(self):
        cleaned_data = super().clean()

        material_fields = ['name', 'make', 'quantity', 'price']
        if not any(cleaned_data.get(field) for field in material_fields):
            # When every field is blank, mark this form for deletion so the
            # inline formset treats it as an empty row and ignores it.
            cleaned_data['DELETE'] = True

        return cleaned_data
        
class ProjectMaterialInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        project_type = None
        project_type_id = self.data.get('project_type') if self.data else None
        if project_type_id:
            project_type = ProjectType.objects.filter(pk=project_type_id).first()

        if not project_type and getattr(self.instance, 'project_type', None):
            project_type = self.instance.project_type

        if project_type and project_type.name.lower() == 'turnkey':
            has_material = False
            for form in self.forms:
                if not hasattr(form, 'cleaned_data'):
                    continue
                if form.cleaned_data.get('DELETE'):
                    continue
                if any(
                    form.cleaned_data.get(field)
                    for field in ['name', 'make', 'quantity', 'price']
                ):
                    has_material = True
                    break

            if not has_material:
                raise forms.ValidationError(
                    'At least one material is required for Turnkey projects.'
                )






class ProjectForm(forms.ModelForm):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    customer_start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    customer_end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))

    class Meta:
        model = Project
        fields = [
            # General
            'name', 'customer_name', 'start_date', 'end_date', 'description',
            'status_type', 'project_type', 'location_type', 'is_onsite',
            'country', 'currency',
            # Billing (Service)
            'rate_type', 'rate_value', 'daily_rate',
            # Budget (Turnkey)
            'budget',
            # Customer contract
            'customer_start_date', 'customer_end_date',
            'customer_currency', 'customer_rate_type', 'customer_rate_value',
            'customer_da_rate_type', 'customer_da_rate_value', 'customer_weekend_rate',
            # Quoted values (Turnkey)
            'quoted_hours', 'quoted_days', 'quoted_price',
            # DA config (config only; computation comes from timesheets)
            'da_type', 'da_rate_per_unit', 'extended_hours_threshold',
            'extended_hours_da_rate', 'off_day_da_rate',
        ]
        labels = {
            'rate_value': 'Customer Billing Rate',
            'daily_rate': 'Employee Daily Rate',
            'da_rate_per_unit': 'DA Rate (per Hour/Day)',
            'extended_hours_da_rate': 'Extra Hours DA Rate',
            'extended_hours_threshold': 'Extra Hours Threshold (Weekly)',
            'off_day_da_rate': 'Weekend Off-Day DA',
            'is_onsite': 'Employee onsite',
        }
        help_texts = {
            'rate_type': 'Choose how you will bill the customer – per hour or per day.',
            'rate_value': 'Enter the rate you are charging the customer based on the selected rate type.',
            'da_type': 'Select if DA should be paid daily or hourly for international projects.',
            'da_rate_per_unit': 'DA amount for Local, Domestic, or International projects.',
            'extended_hours_threshold': 'Hours above which extra DA is paid weekly (e.g., 50).',
            'extended_hours_da_rate': 'DA rate for the hours worked above threshold.',
            'off_day_da_rate': 'Fixed DA for off-days (weekends) in international projects.',
            'budget': 'Total project budget for Turnkey projects.',
            'daily_rate': 'Standard daily charge for Service-based projects.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Styling
        for f in self.fields.values():
            cls = f.widget.attrs.get('class', '')
            parts = set(cls.split())
            if isinstance(f, forms.BooleanField):
                parts.add('form-check-input')
            else:
                parts.add('form-control')
            f.widget.attrs['class'] = ' '.join(sorted(parts))

    def clean(self):
        cleaned = super().clean()

        # Normalize names robustly (tolerate descriptive names like "Turnkey (Fixed …)")
        def norm(x):
            return (x or '').strip().lower()

        pt = cleaned.get('project_type')
        lt = cleaned.get('location_type')
        is_onsite = cleaned.get('is_onsite')

        pt_name = norm(getattr(pt, 'name', None))
        lt_name = norm(getattr(lt, 'name', None))

        def ensure(fields):
            for name in fields:
                if cleaned.get(name) in (None, ''):
                    self.add_error(name, self.fields[name].error_messages.get('required', 'This field is required.'))

        # Conditional requirements
        if 'service' in pt_name:
            ensure([
                'rate_type', 'rate_value',
                'customer_rate_type', 'customer_rate_value',
                'customer_currency',
                'customer_da_rate_type', 'customer_da_rate_value',
                'customer_weekend_rate',
                'customer_start_date', 'customer_end_date',
            ])
        elif 'turnkey' in pt_name:
            ensure(['budget', 'quoted_hours', 'quoted_days', 'quoted_price'])

        if any(tag in lt_name for tag in ['local', 'domestic']):
            ensure(['da_rate_per_unit'])
        elif 'international' in lt_name and is_onsite:
            ensure(['da_rate_per_unit', 'da_type', 'extended_hours_threshold', 'extended_hours_da_rate', 'off_day_da_rate'])

        # Date sanity
        s, e = cleaned.get('start_date'), cleaned.get('end_date')
        if s and e and e < s:
            self.add_error('end_date', 'End date cannot be earlier than start date.')

        cs, ce = cleaned.get('customer_start_date'), cleaned.get('customer_end_date')
        if cs and ce and ce < cs:
            self.add_error('customer_end_date', 'Customer end date cannot be earlier than start date.')

        return cleaned
   


# Formset for project materials
ProjectMaterialFormSet = inlineformset_factory(
    Project,
    ProjectMaterial,
    form=ProjectMaterialForm,
    formset=ProjectMaterialInlineFormSet,
    fields=['name', 'make', 'quantity', 'price'],
    extra=1,
    can_delete=True,
)
