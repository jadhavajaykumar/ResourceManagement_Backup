from django import forms
from datetime import date, timedelta
from project.models import Project  # ✅ imported
from expenses.models import AdvanceRequest
from .models import (
    Expense, ExpenseType, SystemSettings,
    EmployeeExpenseSetting, CountryDASetting, AdvanceRequest
)
from employee.models import EmployeeProfile
from project.services.assignment import get_assigned_projects
# ---------------------- Expense Entry Form ----------------------
from utils.grace_period import get_allowed_grace_days, is_within_grace

# ✅ NEW: we will validate against timesheets
from timesheet.models import Timesheet


import logging
logger = logging.getLogger('expenses')


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

        # Ensure basic accessibility attributes for widgets (helps DevTools warnings)
        for name, field in self.fields.items():
            attrs = field.widget.attrs or {}
            label = field.label or name.replace('_', ' ').capitalize()
            attrs.setdefault('placeholder', label)
            attrs.setdefault('title', label)
            attrs.setdefault('aria-label', label)
            field.widget.attrs = attrs

    def clean_date(self):
        submitted_date = self.cleaned_data['date']
        today = date.today()
        expense_type = self.cleaned_data.get('new_expense_type')

        if submitted_date > today:
            raise forms.ValidationError("Expenses cannot be submitted for future dates.")

        if self.employee:
            grace_days = get_allowed_grace_days(self.employee)
            if not is_within_grace(submitted_date, grace_days):
                raise forms.ValidationError(
                    f"You can only submit expenses within the last {grace_days} days."
                )
            # ✅ Cooldown validation
            if expense_type and getattr(expense_type, 'requires_cooldown', False):
                from expenses.models import Expense as ExpenseModel
                latest_same_type = ExpenseModel.objects.filter(
                    employee=self.employee,
                    new_expense_type=expense_type
                ).order_by('-date').first()

                if latest_same_type:
                    min_allowed_date = latest_same_type.date + timedelta(days=getattr(expense_type, 'cooldown_days', 365) or 365)
                    if submitted_date < min_allowed_date:
                        raise forms.ValidationError(
                            f"You can only submit this expense once every {getattr(expense_type, 'cooldown_days', 365) or 365} days. "
                            f"Last claimed on {latest_same_type.date}. Next eligible date: {min_allowed_date}"
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
        submitted_date = cleaned_data.get('date')

        # ---- TIMESHEET requirement: only if the ExpenseType explicitly requests it ----
        timesheet_required = False
        if expense_type:
            # support multiple possible attribute names on ExpenseType to be robust
            for attr in ('requires_timesheet', 'timesheet_required', 'requires_timesheet_check', 'requires_ts'):
                try:
                    if getattr(expense_type, attr, False):
                        timesheet_required = True
                        break
                except Exception:
                    continue

        if timesheet_required and self.employee and submitted_date:
            # require timesheet with status Pending or Approved (same as before)
            try:
                has_ts = Timesheet.objects.filter(
                    employee=self.employee,
                    date=submitted_date,
                    status__in=["Pending", "Approved"]
                ).exists()
            except Exception as e:
                logger.exception("Timesheet lookup failed: %s", e)
                has_ts = False

            if not has_ts:
                # attach error to date field so user sees it near the date input
                self.add_error(
                    'date',
                    f"Please submit your timesheet for {submitted_date} first, then submit the expense."
                )

        # ---- Existing validation logic (unchanged) ----
        if expense_type:
            # Validate kilometers requirement
            if getattr(expense_type, 'requires_kilometers', False):
                if not kilometers:
                    self.add_error('kilometers', f"Kilometers required for {expense_type.name}.")
                elif getattr(expense_type, 'rate_per_km', None) is None and getattr(expense_type, 'rate', None) is None:
                    self.add_error('new_expense_type', f"Rate per km not defined for {expense_type.name}.")
                else:
                    # try both common attribute names
                    rate = getattr(expense_type, 'rate_per_km', None) or getattr(expense_type, 'rate', 0)
                    try:
                        calculated_amount = float(kilometers) * float(rate)
                        cleaned_data['amount'] = calculated_amount
                        amount = calculated_amount  # update for cap check
                    except Exception:
                        # ignore calculation error but leave validation to max cap/amount presence
                        pass

            # Validate receipt requirement
            if getattr(expense_type, 'requires_receipt', False) and not receipt:
                self.add_error('receipt', f"Receipt required for {expense_type.name}.")

            # Validate amount for non-kilometer-based expenses
            if not getattr(expense_type, 'requires_kilometers', False) and not amount:
                self.add_error('amount', "Amount is required.")

            # Validate travel location fields
            if getattr(expense_type, 'requires_travel_locations', False):
                if not from_location:
                    self.add_error('from_location', "From location is required for this expense type.")
                if not to_location:
                    self.add_error('to_location', "To location is required for this expense type.")

            # Validate max cap if defined
            max_allowed = getattr(expense_type, 'max_amount_allowed', None)
            if max_allowed is not None and amount is not None:
                try:
                    if float(amount) > float(max_allowed):
                        self.add_error('amount', f"Amount exceeds cap of ₹{max_allowed} for this expense type.")
                except Exception:
                    logger.debug("Could not compare amount vs max cap: amount=%s cap=%s", amount, max_allowed)

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
        fields = ['project', 'amount', 'purpose']  # ⛔ Removed 'date_requested'
        widgets = {
            'amount': forms.NumberInput(attrs={'placeholder': 'Enter amount'}),
            'purpose': forms.Textarea(attrs={'placeholder': 'Enter purpose', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)

        if employee:
            assigned_projects = Project.objects.filter(taskassignment__employee=employee).distinct()
            self.fields['project'].queryset = assigned_projects
            self.fields['project'].empty_label = "Select Project"
            self.fields['amount'].widget.attrs.update({'placeholder': 'Enter amount'})
