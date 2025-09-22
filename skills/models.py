# skills/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

# -----------------------------
# Existing models (kept mostly unchanged)
# -----------------------------
class MainSkill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class SubSkill(models.Model):
    main_skill = models.ForeignKey(MainSkill, related_name='subskills', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('main_skill', 'name')

    def __str__(self):
        return f"{self.main_skill.name} - {self.name}"

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

# Existing SkillQuestion + EmployeeAnswer kept unchanged
class SkillQuestion(models.Model):
    main_skill = models.ForeignKey(MainSkill, related_name='questions', on_delete=models.CASCADE)
    subskill = models.ForeignKey('SubSkill', related_name='questions', on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('main_skill', 'subskill', 'order')
        unique_together = ('main_skill', 'subskill', 'order')

    def __str__(self):
        ss = f" / {self.subskill.name}" if self.subskill else ""
        return f"{self.main_skill.name}{ss} - Q{self.order}: {self.text[:40]}"

class EmployeeAnswer(models.Model):
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

# -----------------------------
# Extended EmployeeSkill - keep rating for compatibility, add new fields
# -----------------------------
class EmployeeSkill(models.Model):
    employee = models.ForeignKey('employee.EmployeeProfile', on_delete=models.CASCADE)
    main_skill = models.ForeignKey(MainSkill, on_delete=models.CASCADE)
    subskill = models.ForeignKey(SubSkill, on_delete=models.CASCADE)

    # legacy compatibility: existing code uses 'rating'
    rating = models.PositiveIntegerField(default=0)

    # New fields - optional to avoid breaking migrations on existing DB
    proficiency = models.PositiveSmallIntegerField(null=True, blank=True, help_text="0-100 (preferred) — new standardized field")
    years_experience = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, default=None)
    certified = models.BooleanField(default=False)
    certification_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'subskill')
        ordering = ('employee', 'main_skill__name', 'subskill__name')

    def __str__(self):
        return f"{self.employee} - {self.subskill} ({self.effective_rating})"

    @property
    def effective_rating(self):
        """
        Return new standardized proficiency if present, else fall back to legacy rating.
        Use throughout views to be future-proof.
        """
        if self.proficiency is not None:
            return int(self.proficiency)
        return int(self.rating or 0)

    def set_proficiency_from_rating(self):
        """Convenience: set proficiency from legacy rating if proficiency is empty."""
        if self.proficiency is None and self.rating is not None:
            self.proficiency = int(self.rating)
            self.save(update_fields=['proficiency'])

# -----------------------------
# New models to add: SkillCategory, SkillMatrix, SkillMatrixRow
# -----------------------------
class SkillCategory(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('order', 'name')

    def __str__(self):
        return self.name

# Link main skill to category (optional)
MainSkill.add_to_class('category', models.ForeignKey(SkillCategory, related_name='main_skills', on_delete=models.SET_NULL, null=True, blank=True))

class SkillMatrix(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class SkillMatrixRow(models.Model):
    matrix = models.ForeignKey(SkillMatrix, related_name='rows', on_delete=models.CASCADE)
    main_skill = models.ForeignKey(MainSkill, on_delete=models.PROTECT)
    subskill = models.ForeignKey(SubSkill, on_delete=models.PROTECT)
    required_proficiency = models.PositiveSmallIntegerField(default=50)
    mandatory = models.BooleanField(default=False)

    class Meta:
        unique_together = ('matrix', 'main_skill', 'subskill')
        ordering = ('matrix__name', 'main_skill__name', 'subskill__name')

    def __str__(self):
        return f"{self.matrix.name} → {self.main_skill.name} / {self.subskill.name}"
