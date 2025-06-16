from django.db import models

class ProjectType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class LocationType(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class ProjectStatus(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name



class Project(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('Turnkey', 'Turnkey (Fixed Budget & Duration)'),
        ('Service', 'Service (Daily Rate Billing)'),
    ]
    RATE_TYPE_CHOICES = [
        ('Hourly', 'Hourly'),
        ('Daily', 'Daily'),
    ]
    DA_TYPE_CHOICES = [
        ('Hourly', 'Hourly'),
        ('Daily', 'Daily'),
    ]

    # General Fields
    name = models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status_type = models.ForeignKey('ProjectStatus', on_delete=models.SET_NULL, null=True, verbose_name='Project Status')
    project_type = models.ForeignKey('ProjectType', on_delete=models.SET_NULL, null=True, verbose_name='Project Type')
    location_type = models.ForeignKey('LocationType', on_delete=models.SET_NULL, null=True, verbose_name='Project Location')

    # Country and currency
    country = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)

    # Billing Info - applicable only for Service
    rate_type = models.CharField(max_length=10, choices=RATE_TYPE_CHOICES, blank=True, null=True, verbose_name='Billing Method')
    rate_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Charge Rate to Customer')

    # Budget/Daily Rate - applicable only for Turnkey
    budget = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text="Total budget allocated for Turnkey projects. Used for tracking expenses and DA."
    )
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Employee Daily Rate")

    # DA Configuration
    da_type = models.CharField(max_length=10, choices=DA_TYPE_CHOICES, blank=True, null=True, verbose_name="DA Type (Daily/Hourly)")
    da_rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="DA Rate (per Hour/Day)")

    # Extra DA for International
    extended_hours_threshold = models.IntegerField(blank=True, null=True, verbose_name="Extra Hours Threshold (Weekly)")
    extended_hours_da_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="DA Rate for Extra Hours")

    # Weekend Off-Day DA (International only)
    off_day_da_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Weekend Off-Day DA")

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
