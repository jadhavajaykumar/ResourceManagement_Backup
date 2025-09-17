# skills/forms.py
from django import forms
from django.core.exceptions import ValidationError

# import all models used by forms
from .models import (
    MainSkill,
    SubSkill,
    EmployeeSkill,
    SkillQuestion,
    EmployeeAnswer,
)

# employee app model used in AssignSkillForm for FK to employee profile
try:
    from employee.models import EmployeeProfile
except Exception:
    # If employee app not available while you're moving code, keep a fallback to avoid import-time crash.
    EmployeeProfile = None


class MainSkillForm(forms.ModelForm):
    """
    Form to create/update MainSkill. Keeps one non-model 'description' field
    as a regular form field (if you still want to show it).
    """
    description = forms.CharField(required=False)

    class Meta:
        model = MainSkill
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if getattr(self, 'instance', None) and hasattr(self.instance, 'description'):
            self.fields['description'].initial = getattr(self.instance, 'description', '')


class SubSkillForm(forms.ModelForm):
    class Meta:
        model = SubSkill
        fields = ['main_skill', 'name']

    def clean(self):
        cleaned = super().clean()
        main = cleaned.get('main_skill')
        if main is None:
            raise ValidationError("Main skill is required for a subskill.")
        return cleaned


class AssignSkillForm(forms.ModelForm):
    class Meta:
        model = EmployeeSkill
        fields = ['employee', 'main_skill', 'subskill', 'rating']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if EmployeeProfile is None and 'employee' in self.fields:
            self.fields['employee'].required = False

    def clean(self):
        cleaned = super().clean()
        main = cleaned.get('main_skill')
        sub = cleaned.get('subskill')
        if main and sub and getattr(sub, 'main_skill_id', None) != getattr(main, 'id', None):
            raise ValidationError("Selected subskill does not belong to the selected main skill.")
        return cleaned


# ---------- New forms for Q&A & evaluation ----------
class SkillQuestionForm(forms.ModelForm):
    class Meta:
        model = SkillQuestion
        fields = ['main_skill', 'subskill', 'order', 'text']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subskill'].required = False
        self.fields['main_skill'].required = True


class EmployeeAnswerForm(forms.ModelForm):
    class Meta:
        model = EmployeeAnswer
        fields = ['answer_text']
