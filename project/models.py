from django.db import models
from django.conf import settings
from django.utils import timezone

PROJECT_TYPES = (
    ('Turnkey', 'Turnkey'),
    ('Service', 'Service'),
)

BILLING_METHODS = (
    ('Hourly', 'Hourly'),
    ('Daily', 'Daily'),
)

LOCATIONS = (
    ('Local', 'Local'),
    ('Domestic', 'Domestic'),
    ('International', 'International'),
)

STATUS_CHOICES = (
    ('Not Started', 'Not Started'),
    ('In Progress', 'In Progress'),
    ('On Hold', 'On Hold'),
    ('Completed', 'Completed'),
    ('Cancelled', 'Cancelled'),
)

class Project(models.Model):
    name = models.CharField(max_length=100)
    customer_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES)
    billing_method = models.CharField(max_length=20, choices=BILLING_METHODS)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # Turnkey projects
    daily_hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # Service projects
    location = models.CharField(max_length=20, choices=LOCATIONS)
    
    country_rate = models.ForeignKey(CountryRate, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.CharField(max_length=20, choices=LOCATIONS)
    
    
    
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Started')
    documents = models.FileField(upload_to='project_documents/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.customer_name})"

class Task(models.Model):
    project = models.ForeignKey(Project, related_name='tasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField()
    progress = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

class Subtask(models.Model):
    task = models.ForeignKey(Task, related_name='subtasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class ProjectExpensePolicy(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE)
    allow_transport = models.BooleanField(default=True)
    allow_accommodation = models.BooleanField(default=False)
    allow_safety_shoes = models.BooleanField(default=False)
    safety_shoe_tracker_days = models.PositiveIntegerField(default=365)
    mobile_recharge_limit = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    domestic_transport_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    international_transport_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Expense Policy ({self.project.name})"

class CountryDASettings(models.Model):
    country_name = models.CharField(max_length=100, unique=True)
    currency_code = models.CharField(max_length=10)
    da_rate_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hour_rate = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.country_name} ({self.currency_code})"

