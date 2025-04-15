from django import forms
from .models import Expense, ExpenseType

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['project', 'expense_type', 'date', 'kilometers', 'amount', 'receipt', 'comments']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

def clean(self):
        cleaned_data = super().clean()
        expense_type = cleaned_data.get('expense_type')
        kilometers = cleaned_data.get('kilometers')
        amount = cleaned_data.get('amount')
        receipt = cleaned_data.get('receipt')

        if expense_type:  # Changed to work with ExpenseType object
            if expense_type.requires_kilometers:
                if not kilometers:
                    self.add_error('kilometers', f"Kilometers required for {expense_type.name}.")
                else:
                    # Calculate using dynamic rate
                    cleaned_data['amount'] = kilometers * expense_type.rate_per_km

            if expense_type.requires_receipt and not receipt:
                self.add_error('receipt', f"Receipt required for {expense_type.name}.")

            if not expense_type.requires_kilometers and not amount:
                self.add_error('amount', "Amount required.")
        
        return cleaned_data
        
        
        