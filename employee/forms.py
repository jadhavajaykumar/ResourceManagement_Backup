# employee/forms.py
from django import forms
from django.contrib import admin
from .models import EmployeeProfile
from timesheet.models import CompOffApplication

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = '__all__'
    
    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role == 'Admin' and not self.instance.user.has_perm('timesheet.can_approve'):
            raise forms.ValidationError("Only authorized users can be assigned Admin role.")
        return role

# Update the admin class to use the form
class EmployeeProfileAdmin(admin.ModelAdmin):
    form = EmployeeProfileForm
    # ... rest of the admin class ...
    
# employee/forms.py


from django import forms
from timesheet.models import CompOffApplication



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
