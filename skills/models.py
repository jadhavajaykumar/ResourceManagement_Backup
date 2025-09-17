# skills/models.py
from django.db import models

class MainSkill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class SubSkill(models.Model):
    main_skill = models.ForeignKey(MainSkill, related_name='subskills', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('main_skill', 'name')

    def __str__(self):
        return f"{self.main_skill.name} - {self.name}"

class EmployeeSkill(models.Model):
    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    main_skill = models.ForeignKey(MainSkill, on_delete=models.CASCADE)
    subskill = models.ForeignKey(SubSkill, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('employee', 'subskill')

    def __str__(self):
        return f"{self.employee} - {self.subskill} ({self.rating})"

class TaskAssignment(models.Model):
    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE)
    task = models.ForeignKey('project.Task', on_delete=models.CASCADE)
    assigned_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'task')
        ordering = ['-assigned_date']

    def __str__(self):
        return f"{self.employee} → {self.project} → {self.task}"

# ----------------- NEW MODELS for Q&A & Manager Rating -----------------



class EmployeeAnswer(models.Model):
    """
    Stores employee's answer to a SkillQuestion and manager's rating (0-4).
    Use a string reference to the SkillQuestion model to avoid load-order issues.
    """
    employee = models.ForeignKey('employee.EmployeeProfile', related_name='skill_answers', on_delete=models.CASCADE)
    question = models.ForeignKey('skills.SkillQuestion', related_name='answers', on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True, null=True)
    manager_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    manager_notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'question')

    def __str__(self):
        return f"{self.employee} - {self.question} (rating={self.manager_rating})"


class SkillQuestion(models.Model):
    """
    A question which may be linked to a MainSkill and (optionally) to a SubSkill.
    We add 'subskill' so questions can be specific to a SubSkill.
    """
    main_skill = models.ForeignKey(MainSkill, related_name='questions', on_delete=models.CASCADE)
    subskill = models.ForeignKey('SubSkill', related_name='questions', on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        # order uniqueness should be per (main_skill, subskill)
        ordering = ('main_skill', 'subskill', 'order')
        unique_together = ('main_skill', 'subskill', 'order')

    def __str__(self):
        ss = f" / {self.subskill.name}" if self.subskill else ""
        return f"{self.main_skill.name}{ss} - Q{self.order}: {self.text[:40]}"

