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