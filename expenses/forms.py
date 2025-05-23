from django import forms
from datetime import date, timedelta

from .models import (
    Expense, ExpenseType, SystemSettings,
    EmployeeExpenseSetting, CountryDASetting
)
from employee.models import EmployeeProfile
from project.services.assignment import get_assigned_projects


# ---------------------- Expense Entry Form ----------------------
class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['project', 'new_expense_type', 'date', 'kilometers', 'amount', 'receipt', 'comments']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'new_expense_type': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)

        self.fields['new_expense_type'].queryset = ExpenseType.objects.all()

        if employee:
            self.fields['project'].queryset = get_assigned_projects(employee)

    def clean_date(self):
        submitted_date = self.cleaned_data['date']
        today = date.today()
        grace_period = SystemSettings.objects.first().expense_grace_days or 10

        if submitted_date > today:
            raise forms.ValidationError("Expenses cannot be submitted for future dates.")
        if submitted_date < (today - timedelta(days=grace_period)):
            raise forms.ValidationError(f"You can only submit expenses within the last {grace_period} days.")
        return submitted_date

    def clean(self):
        cleaned_data = super().clean()
        expense_type = cleaned_data.get('new_expense_type')
        kilometers = cleaned_data.get('kilometers')
        amount = cleaned_data.get('amount')
        receipt = cleaned_data.get('receipt')

        if expense_type:
            if expense_type.requires_kilometers:
                if not kilometers:
                    self.add_error('kilometers', f"Kilometers required for {expense_type.name}.")
                else:
                    cleaned_data['amount'] = kilometers * expense_type.rate_per_km

            if expense_type.requires_receipt and not receipt:
                self.add_error('receipt', f"Receipt required for {expense_type.name}.")

            if not expense_type.requires_kilometers and not amount:
                self.add_error('amount', "Amount required.")

        return cleaned_data


# ---------------------- Global Grace Period Settings ----------------------
class GracePeriodForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = ['expense_grace_days']
        widgets = {
            'expense_grace_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'expense_grace_days': 'Allowed Grace Period (in days)',
        }


# ---------------------- Per-Employee Grace Period ----------------------
class EmployeeGracePeriodForm(forms.ModelForm):
    employee = forms.ModelChoiceField(queryset=EmployeeProfile.objects.all(), required=True)

    class Meta:
        model = EmployeeExpenseSetting
        fields = ['employee', 'grace_period_days']


# ---------------------- Country DA Rate Form ----------------------
class CountryDASettingForm(forms.ModelForm):
    class Meta:
        model = CountryDASetting
        fields = ['country', 'currency', 'da_rate_per_hour', 'extra_hour_rate']
        widgets = {
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country Name'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Currency Code (e.g., INR, USD)'}),
            'da_rate_per_hour': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'extra_hour_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
