from django import forms
from datetime import date, timedelta
from manager.models import TaskAssignment
from project.models import Project
from project.models import Project  # ✅ imported


from .models import (
    Expense, ExpenseType, SystemSettings,
    EmployeeExpenseSetting, CountryDASetting, AdvanceRequest
)
from employee.models import EmployeeProfile
from project.services.assignment import get_assigned_projects
# ---------------------- Expense Entry Form ----------------------
from utils.grace_period import get_allowed_grace_days, is_within_grace


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'project',
            'new_expense_type',
            'date',
            'kilometers',
            'amount',
            'receipt',
            'comments',
            'from_location',
            'to_location'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'new_expense_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)

        self.fields['new_expense_type'].queryset = ExpenseType.objects.all()

        self.fields['from_location'].widget = forms.TextInput(attrs={'placeholder': 'From'})
        self.fields['to_location'].widget = forms.TextInput(attrs={'placeholder': 'To'})

        if self.employee:
            self.fields['project'].queryset = get_assigned_projects(self.employee)

    def clean_date(self):
        submitted_date = self.cleaned_data['date']
        today = date.today()

        if submitted_date > today:
            raise forms.ValidationError("Expenses cannot be submitted for future dates.")

        if self.employee:
            grace_days = get_allowed_grace_days(self.employee)
            if not is_within_grace(submitted_date, grace_days):
                raise forms.ValidationError(
                    f"You can only submit expenses within the last {grace_days} days."
                )

        return submitted_date

    def clean(self):
        cleaned_data = super().clean()
        expense_type = cleaned_data.get('new_expense_type')
        kilometers = cleaned_data.get('kilometers')
        amount = cleaned_data.get('amount')
        receipt = cleaned_data.get('receipt')
        from_location = cleaned_data.get('from_location')
        to_location = cleaned_data.get('to_location')

        if expense_type:
            # ✅ Validate kilometers requirement
            if expense_type.requires_kilometers:
                if not kilometers:
                    self.add_error('kilometers', f"Kilometers required for {expense_type.name}.")
                elif expense_type.rate_per_km is None:
                    self.add_error('new_expense_type', f"Rate per km not defined for {expense_type.name}.")
                else:
                    calculated_amount = kilometers * expense_type.rate_per_km
                    cleaned_data['amount'] = calculated_amount
                    amount = calculated_amount  # update for cap check

            # ✅ Validate receipt requirement
            if expense_type.requires_receipt and not receipt:
                self.add_error('receipt', f"Receipt required for {expense_type.name}.")

            # ✅ Validate amount for non-kilometer-based expenses
            if not expense_type.requires_kilometers and not amount:
                self.add_error('amount', "Amount is required.")

            # ✅ Validate travel location fields
            if expense_type.requires_travel_locations:
                if not from_location:
                    self.add_error('from_location', "From location is required for this expense type.")
                if not to_location:
                    self.add_error('to_location', "To location is required for this expense type.")

            # ✅ Validate max cap if defined
            if expense_type.max_amount_allowed is not None and amount is not None:
                if amount > expense_type.max_amount_allowed:
                    self.add_error('amount', f"Amount exceeds cap of ₹{expense_type.max_amount_allowed} for this expense type.")

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



# ---------------------- Advance request Form ----------------------
class AdvanceRequestForm(forms.ModelForm):
    class Meta:
        model = AdvanceRequest
        fields = ['project', 'amount', 'purpose']

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee')
        super().__init__(*args, **kwargs)
         # ✅ Correct assignment logic using TaskAssignment
        assigned_projects = Project.objects.filter(taskassignment__employee=employee).distinct()
        self.fields['project'].queryset = assigned_projects
