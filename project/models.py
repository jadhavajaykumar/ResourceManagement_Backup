from django.db import models

class ProjectType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class LocationType(models.Model):
    name = models.CharField(max_length=100)

class ProjectStatus(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Project(models.Model):
    name = models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status_type = models.CharField(max_length=100, null=True, blank=True)
    project_type = models.CharField(max_length=100, null=True, blank=True)
    location_type = models.ForeignKey(LocationType, on_delete=models.SET_NULL, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    rate_type = models.CharField(max_length=10, choices=[('Hourly', 'Hourly'), ('Daily', 'Daily')], blank=True, null=True)
    rate_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    da_rate_per_day = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    extended_hours_threshold = models.IntegerField(blank=True, null=True)
    extended_hours_da_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.name

class DASetting(models.Model):
    location_type = models.ForeignKey(LocationType, on_delete=models.CASCADE)
    min_hours = models.IntegerField(default=6)
    da_amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f'{self.location_type.name} → {self.da_amount}'

class Task(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='tasks')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    progress = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.project.name} - {self.name}"

class Subtask(models.Model):
    task = models.ForeignKey('Task', related_name='subtasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class ProjectExpensePolicy(models.Model):
    project = models.OneToOneField('Project', on_delete=models.CASCADE)
    allow_transport = models.BooleanField(default=True)
    allow_accommodation = models.BooleanField(default=False)
    allow_safety_shoes = models.BooleanField(default=False)
    safety_shoe_tracker_days = models.PositiveIntegerField(default=365)
    mobile_recharge_limit = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    domestic_transport_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    international_transport_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Expense Policy ({self.project.name})"

class ProjectRequiredSkill(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='required_skills')
    main_skill = models.ForeignKey('manager.MainSkill', on_delete=models.CASCADE)
    subskill = models.ForeignKey('manager.SubSkill', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.project.name} → {self.main_skill.name} → {self.subskill.name}"
