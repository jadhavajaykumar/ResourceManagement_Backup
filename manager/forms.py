# manager/forms.py

from django import forms
from project.models import Project, Task
from .models import MainSkill, SubSkill, EmployeeSkill, TaskAssignment


class MainSkillForm(forms.ModelForm):
    class Meta:
        model = MainSkill
        fields = ['name']


class SubSkillForm(forms.ModelForm):
    class Meta:
        model = SubSkill
        fields = ['main_skill', 'name']


class AssignSkillForm(forms.ModelForm):
    class Meta:
        model = EmployeeSkill
        fields = ['employee', 'main_skill', 'subskill', 'rating']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['main_skill'].queryset = MainSkill.objects.all()

        if 'main_skill' in self.data:
            try:
                main_skill_id = int(self.data.get('main_skill'))
                self.fields['subskill'].queryset = SubSkill.objects.filter(main_skill_id=main_skill_id)
            except (ValueError, TypeError):
                self.fields['subskill'].queryset = SubSkill.objects.none()
        elif self.initial.get('main_skill'):
            self.fields['subskill'].queryset = SubSkill.objects.filter(main_skill=self.initial['main_skill'])
        else:
            self.fields['subskill'].queryset = SubSkill.objects.none()


class TaskAssignmentForm(forms.ModelForm):
    role_filter = forms.ChoiceField(choices=[], required=False)

    class Meta:
        model = TaskAssignment
        fields = ['employee', 'project', 'task', 'manager_notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['project'].required = False
        self.fields['task'].required = False

        # Dynamically set role_filter choices at runtime
        try:
            from employee.models import EmployeeProfile
            roles = EmployeeProfile.objects.values_list('role', flat=True).distinct()
            self.fields['role_filter'].choices = [('', 'All Roles')] + [(r, r) for r in roles]
        except Exception:
            self.fields['role_filter'].choices = [('', 'All Roles')]

        if 'project' in self.data:
            try:
                project_id = int(self.data.get('project'))
                self.fields['task'].queryset = Task.objects.filter(project_id=project_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.project:
            self.fields['task'].queryset = self.instance.project.task_set.all()



