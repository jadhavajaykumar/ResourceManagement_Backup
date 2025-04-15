# manager/forms.py
 
from project.models import Project, Task
from employee.models import EmployeeProfile
from django import forms
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

        # Set all main skills by default
        self.fields['main_skill'].queryset = MainSkill.objects.all()

        # Set subskill queryset based on posted or initial main_skill
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
    role_filter = forms.ChoiceField(choices=[('', 'All Roles')] + [(role, role) for role in EmployeeProfile.objects.values_list('role', flat=True).distinct()], required=False)
    #role_filter = forms.ChoiceField(choices=[], required=False)  # Temporary empty choices
    class Meta:
        model = TaskAssignment
        fields = ['employee', 'project', 'task', 'manager_notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].required = False
        self.fields['task'].required = False
        #self.fields['employee'].queryset = EmployeeProfile.objects.filter(role='Technician')
        if 'project' in self.data:
            try:
                project_id = int(self.data.get('project'))
                self.fields['task'].queryset = Task.objects.filter(project_id=project_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['task'].queryset = self.instance.project.task_set


