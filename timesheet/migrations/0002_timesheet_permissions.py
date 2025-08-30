from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('timesheet', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='timesheet',
            options={'permissions': [('can_approve', 'Can approve timesheets')]},
        ),
    ]
    