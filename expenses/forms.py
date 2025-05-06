from django import forms
from .models import Expense, ExpenseType, SystemSettings
from django import forms
from .models import EmployeeExpenseSetting
from employee.models import EmployeeProfile
from datetime import date, timedelta


#from core.models import SystemSettings

class ExpenseForm(forms.ModelForm):
    new_expense_type = forms.ModelChoiceField(
        queryset=ExpenseType.objects.all(),   # ✅ Dynamically pull Expense Types added by Manager
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )

    class Meta:
        model = Expense
        fields = ['project', 'new_expense_type', 'date', 'kilometers', 'amount', 'receipt', 'comments']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_expense_type = cleaned_data.get('expense_type')
        kilometers = cleaned_data.get('kilometers')
        amount = cleaned_data.get('amount')
        receipt = cleaned_data.get('receipt')

        if new_expense_type:
            if new_expense_type.requires_kilometers:
                if not kilometers:
                    self.add_error('kilometers', f"Kilometers required for {new_expense_type.name}.")
                else:
                    cleaned_data['amount'] = kilometers * new_expense_type.rate_per_km

            if new_expense_type.requires_receipt and not receipt:
                self.add_error('receipt', f"Receipt required for {new_expense_type.name}.")

            if not new_expense_type.requires_kilometers and not amount:
                self.add_error('amount', "Amount required.")

        return cleaned_data
        
    def clean_date(self):
        submitted_date = self.cleaned_data['date']
        today = date.today()

        # Fetch dynamic grace period from SystemSettings model
        grace_period = SystemSettings.objects.first().expense_grace_days or 10

        if submitted_date > today:
            raise forms.ValidationError("Expenses cannot be submitted for future dates.")
        if submitted_date < (today - timedelta(days=grace_period)):
            raise forms.ValidationError(f"You can only submit expenses within the last {grace_period} days.")
        return submitted_date    
  # assume where grace period is stored


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

# Setting related to Expenses 
class EmployeeGracePeriodForm(forms.ModelForm):
    employee = forms.ModelChoiceField(queryset=EmployeeProfile.objects.all(), required=True)

    class Meta:
        model = EmployeeExpenseSetting
        fields = ['employee', 'grace_period_days']
