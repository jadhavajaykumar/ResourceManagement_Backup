# employee/forms.py
from django import forms
from django.contrib import admin
from .models import EmployeeProfile
from timesheet.models import CompOffApplication
from django.utils import timezone
from accounts.models import CustomUser
from django.core.exceptions import ValidationError

class CompOffApplicationForm(forms.ModelForm):
    class Meta:
        model = CompOffApplication
        exclude = ['employee', 'date_requested', 'status']  # Do not include system-handled fields

    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.employee:
            instance.employee = self.employee
        if commit:
            instance.save()
        return instance


class EmployeeProfileForm(forms.ModelForm):
    """
    Improved EmployeeProfileForm:
     - explicit fields ordering
     - bootstrap-friendly widgets
     - user selection via ModelChoiceField (HR/admin selects existing user)
     - employee_id is required and validated for uniqueness here (no auto-generation)
    """
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.all().order_by('first_name', 'last_name', 'email'),
        required=True,
        label="Linked User Account",
        help_text="Select an existing user to link to this employee profile."
    )

    class Meta:
        model = EmployeeProfile
        # explicit fields order to control layout
        fields = [
            'user', 'employee_id', 'role', 'department', 'reporting_manager', 'employment_type',
            'career_start_date', 'probotix_joining_date', 'confirmation_date', 'date_of_birth',
            'contact_number', 'address',
            'emergency_contact_name', 'emergency_contact_relation', 'emergency_contact_number',
            'pan_aadhar_ssn', 'bank_account_number', 'bank_ifsc_code', 'epf_number', 'grace_period_days',
        ]
        widgets = {
            # NOTE: placeholder updated to indicate manual entry (no auto-generation)
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Employee ID (required)'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'reporting_manager': forms.Select(attrs={'class': 'form-select'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'career_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'probotix_joining_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'confirmation_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'pan_aadhar_ssn': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_ifsc_code': forms.TextInput(attrs={'class': 'form-control'}),
            'epf_number': forms.TextInput(attrs={'class': 'form-control'}),
            'grace_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add bootstrap classes to user/reporting_manager widgets
        self.fields['user'].widget.attrs.update({'class': 'form-select'})
        self.fields['reporting_manager'].queryset = CustomUser.objects.all().order_by('first_name', 'last_name')
        self.fields['reporting_manager'].widget.attrs.update({'class': 'form-select'})

        # If instance exists, set initial for user
        if self.instance and getattr(self.instance, 'user', None):
            self.fields['user'].initial = self.instance.user

    def clean_employee_id(self):
        """
        Enforce that employee_id is provided and is unique (unless it belongs to the same instance).
        This replaces previous auto-generation behaviour.
        """
        emp_id = self.cleaned_data.get('employee_id')
        if not emp_id or str(emp_id).strip() == '':
            raise ValidationError("Employee ID is required and must be entered manually.")
        emp_id = str(emp_id).strip()

        qs = EmployeeProfile.objects.filter(employee_id=emp_id)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This Employee ID is already in use. Please provide a unique Employee ID.")
        return emp_id

    def clean_role(self):
        role = self.cleaned_data.get('role')
        # maintain previous behavior: require the linked user to have permission for Admin role
        user = self.cleaned_data.get('user') or getattr(self.instance, 'user', None)
        if role == 'Admin' and user and not user.has_perm('timesheet.can_approve'):
            raise forms.ValidationError("Only authorized users can be assigned Admin role.")
        return role


# Update the admin class to use the form (kept for compatibility)
class EmployeeProfileAdmin(admin.ModelAdmin):
    form = EmployeeProfileForm
