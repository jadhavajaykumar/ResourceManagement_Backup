# skills/migrations/000X_backfill_proficiency.py
from django.db import migrations, models
from django.db.models import F

def forwards_populate_proficiency(apps, schema_editor):
    EmployeeSkill = apps.get_model('skills', 'EmployeeSkill')
    # Only populate where proficiency is NULL and rating is NOT NULL
    # Use a single UPDATE query for efficiency.
    EmployeeSkill.objects.filter(proficiency__isnull=True).filter(rating__isnull=False).update(proficiency=F('rating'))

def reverse_unset_populated_proficiency(apps, schema_editor):
    EmployeeSkill = apps.get_model('skills', 'EmployeeSkill')
    # Revert only those rows where proficiency equals rating (best-effort), set proficiency back to NULL.
    # Be careful: this will nullify proficiencies that exactly matched rating.
    EmployeeSkill.objects.filter(proficiency__isnull=False).filter(proficiency=F('rating')).update(proficiency=None)

class Migration(migrations.Migration):

    dependencies = [
        # Replace '0004_alter_skillquestion_options_and_more' with the last existing migration in skills app,
        # e.g. ('skills', '0003_add_proficiency') or use the empty-migration name made earlier
        ('skills', '0006_skillcategory_skillmatrix_and_more')
    ]

    operations = [
        migrations.RunPython(forwards_populate_proficiency, reverse_unset_populated_proficiency),
    ]
