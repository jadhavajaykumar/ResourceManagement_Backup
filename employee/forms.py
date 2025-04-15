# employee/forms.py
from django import forms
from django.contrib import admin
from .models import EmployeeProfile

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = '__all__'
    
    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role == 'Admin' and not self.instance.user.is_superuser:
            raise forms.ValidationError("Only superusers can be assigned Admin role.")
        return role

# Update the admin class to use the form
class EmployeeProfileAdmin(admin.ModelAdmin):
    form = EmployeeProfileForm
    # ... rest of the admin class ...