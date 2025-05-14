# manager/models.py
from django.db import models
from accounts.models import CustomUser
from employee.models import EmployeeProfile
from django.utils import timezone
#from manager.models import SubSkill  # adjust path if needed


class SkillCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Skill(models.Model):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.category.name} → {self.name}"





class MainSkill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class SubSkill(models.Model):
    main_skill = models.ForeignKey(MainSkill, on_delete=models.CASCADE, related_name='subskills')
    name = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ('main_skill', 'name')
    def __str__(self):
        return f"{self.main_skill.name} → {self.name}"

class EmployeeSkill(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    main_skill = models.ForeignKey(MainSkill, on_delete=models.CASCADE)
    subskill = models.ForeignKey(SubSkill, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(5)], default=0)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.main_skill.name} - {self.subskill.name} ({self.rating})"
        
        





# (No direct imports from project.models)

class TaskAssignment(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE, null=True, blank=True)  # ✅ Add null=True, blank=True here
    task = models.ForeignKey('project.Task', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_date = models.DateField(default=timezone.now)
    manager_notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.task and not self.project:
            self.project = self.task.project
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.project.name if self.project else 'No Project'} - {self.task.name if self.task else 'No Task'}"



class SkillAssignment(models.Model):
    employee = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    subskill = models.ForeignKey('manager.SubSkill', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(5)])

    def __str__(self):
        return f"{self.employee} - {self.subskill} ({self.rating})"

        