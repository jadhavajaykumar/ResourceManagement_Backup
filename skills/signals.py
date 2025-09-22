# skills/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from employee.models import EmployeeProfile
from .models import EmployeeSkill, MainSkill, SubSkill, SkillMatrix

@receiver(post_save, sender=EmployeeProfile)
def on_employee_created(sender, instance, created, **kwargs):
    if not created:
        return
    # Option A: create placeholders for all active MainSkill+first SubSkill
    # You may prefer to create none and only create based on matrix or import
    main_skills = MainSkill.objects.filter(active=True).prefetch_related('subskills')[:10]  # limit for safety
    created_count = 0
    for m in main_skills:
        ss = m.subskills.first()
        if ss:
            EmployeeSkill.objects.get_or_create(
                employee=instance,
                main_skill=m,
                subskill=ss,
                defaults={'proficiency': 0, 'years_experience': 0}
            )
            created_count += 1
    # Optionally use SkillMatrix based on employee.designation (if present) to seed required skills
    # matrix_name = getattr(instance, 'designation', None)
    # if matrix_name:
    #     try:
    #         matrix = SkillMatrix.objects.get(name__iexact=matrix_name)
    #         for row in matrix.rows.all():
    #             EmployeeSkill.objects.get_or_create( ... )
    #     except SkillMatrix.DoesNotExist:
    #         pass
