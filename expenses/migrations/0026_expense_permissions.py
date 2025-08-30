from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('expenses', '0010_advanceadjustmentlog'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='expense',
            options={'permissions': [('can_settle', 'Can settle expenses')]},
        ),
    ]