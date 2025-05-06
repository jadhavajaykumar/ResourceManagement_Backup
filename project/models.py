from django.db import models
      
from manager.models import MainSkill, SubSkill, EmployeeSkill  # ✅ Import MainSkill and SubSkill here

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


class CountryDARate(models.Model):
    country = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=10)
    da_rate_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hour_rate = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.country} - {self.currency}"


class Project(models.Model):
    name = models.CharField(max_length=100, verbose_name="Project Name")
    customer_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=20, choices=LOCATIONS)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES, blank=True, null=True)
    billing_method = models.CharField(max_length=20, choices=BILLING_METHODS, blank=True, null=True, verbose_name="Billing Type")
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    daily_hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    country_rate = models.ForeignKey(CountryDARate, on_delete=models.SET_NULL, null=True, blank=True)
    da_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    extra_hour_da_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Started')
    skills_required = models.TextField(blank=True, null=True)
    documents = models.FileField(upload_to='project_documents/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.customer_name})"
    def get_suggested_employees(self):
        from employee.models import EmployeeProfile  # Import here to avoid circular import

        required_subskills = self.required_skills.values_list('subskill_id', flat=True)

        employee_match_data = []

        employees = EmployeeProfile.objects.all()

        for employee in employees:
            employee_skills = EmployeeSkill.objects.filter(employee=employee)

            matched_skills = employee_skills.filter(subskill_id__in=required_subskills)
            total_required = required_subskills.count()

            if total_required == 0:
                match_percentage = 0
            else:
                match_percentage = (matched_skills.count() / total_required) * 100

            # Sum ratings for matched skills
            total_rating = sum(matched_skills.values_list('rating', flat=True))

            if matched_skills.exists():
                employee_match_data.append({
                    'employee': employee,
                    'match_percentage': match_percentage,
                    'total_rating': total_rating,
                })

        # Sort by highest match % first, then by highest rating
        employee_match_data.sort(key=lambda x: (-x['match_percentage'], -x['total_rating']))

        return employee_match_data

#class Task(models.Model):
   # project = models.ForeignKey(Project, related_name='tasks', on_delete=models.CASCADE)
   # name = models.CharField(max_length=200)
   # description = models.TextField(blank=True, null=True)
   # due_date = models.DateField()
  #  progress = models.PositiveIntegerField(default=0)

  #  def __str__(self):
   #     return f"{self.name} ({self.project.name})"
class Task(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='tasks')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)  # ✅ add this
    progress = models.PositiveIntegerField(default=0)    # ✅ add this
    is_completed = models.BooleanField(default=False)

    #def __str__(self):
        #return f"{self.project.project_name} - {self.name}"

    def __str__(self):
        return f"{self.project.name} - {self.name}"


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
        


class ProjectRequiredSkill(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='required_skills')
    main_skill = models.ForeignKey(MainSkill, on_delete=models.CASCADE)
    subskill = models.ForeignKey(SubSkill, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.project.name} → {self.main_skill.name} → {self.subskill.name}"
        