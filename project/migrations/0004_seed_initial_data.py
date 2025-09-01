from django.db import migrations


def seed_data(apps, schema_editor):
    Project = apps.get_model('project', 'Project')
    ProjectMaterial = apps.get_model('project', 'ProjectMaterial')

    for project in Project.objects.filter(customer_rate_type__isnull=True):
        project.customer_rate_type = 'Daily'
        project.save()

    first_project = Project.objects.first()
    if first_project and not first_project.materials.exists():
        ProjectMaterial.objects.create(
            project=first_project,
            name='Sample Material',
            make='Generic',
            quantity=1,
            price=0,
        )


def unseed_data(apps, schema_editor):
    Project = apps.get_model('project', 'Project')
    ProjectMaterial = apps.get_model('project', 'ProjectMaterial')
    Project.objects.filter(customer_rate_type='Daily').update(customer_rate_type=None)
    ProjectMaterial.objects.filter(name='Sample Material', make='Generic').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0003_project_customer_fields_and_material'),
    ]

    operations = [
        migrations.RunPython(seed_data, unseed_data),
    ]