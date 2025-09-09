# approvals/migrations/000Y_make_action_type_required_remove_approved.py
from django.db import migrations, models
import django.db.models.deletion



class Migration(migrations.Migration):

    dependencies = [
        ("approvals", "0003_backfill_action_type"),  # set to the filename used above (without .py)
    ]

    operations = [
        migrations.AlterField(
            model_name="approvalaction",
            name="action_type",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="approvals.approvalactiontype"),
        ),
        migrations.RemoveField(
            model_name="approvalaction",
            name="approved",
        ),
    ]
