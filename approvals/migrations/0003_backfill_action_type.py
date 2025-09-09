# approvals/migrations/000X_backfill_action_type.py
from django.db import migrations, transaction


def create_common_action_types(apps, schema_editor):
    ApprovalActionType = apps.get_model("approvals", "ApprovalActionType")
    common = [
        ("approve", "Approve", "Approve and forward or complete the instance", True),
        ("reject", "Reject", "Reject and close the instance", True),
        ("forward_to_manager", "Forward to Manager", "Forward to manager for review", False),
        ("forward_to_account_manager", "Forward to Account Manager", "Forward to account manager", False),
        ("settle_cash", "Settle by Cash", "Mark as settled by cash and close", True),
    ]
    for slug, label, desc, ends in common:
        ApprovalActionType.objects.get_or_create(
            slug=slug, defaults={"label": label, "description": desc, "ends_flow": ends}
        )


def backfill_action_type(apps, schema_editor):
    ApprovalAction = apps.get_model("approvals", "ApprovalAction")
    ApprovalActionType = apps.get_model("approvals", "ApprovalActionType")

    create_common_action_types(apps, schema_editor)

    approve_tt = ApprovalActionType.objects.filter(slug="approve").first()
    reject_tt = ApprovalActionType.objects.filter(slug="reject").first()
    if not (approve_tt and reject_tt):
        return

    with transaction.atomic():
        to_fix = ApprovalAction.objects.filter(action_type__isnull=True)
        for act in to_fix:
            # If legacy 'approved' column exists, use it. Otherwise default to approve.
            approved_val = None
            if hasattr(act, "approved"):
                approved_val = getattr(act, "approved", None)

            if approved_val is True:
                act.action_type = approve_tt
            elif approved_val is False:
                act.action_type = reject_tt
            else:
                act.action_type = approve_tt
            act.save(update_fields=["action_type"])


class Migration(migrations.Migration):

    dependencies = [
        ("approvals", "0002_approvalactiontype_alter_approvalaction_options_and_more"),
    ]

    operations = [
        migrations.RunPython(create_common_action_types, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(backfill_action_type, reverse_code=migrations.RunPython.noop),
    ]
