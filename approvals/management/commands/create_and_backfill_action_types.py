# approvals/management/commands/create_and_backfill_action_types.py
from django.core.management.base import BaseCommand
from approvals.models import ApprovalActionType, ApprovalAction
from django.db import transaction

COMMON_ACTIONS = [
    ("approve", "Approve", "Approve and forward or complete the instance", True),
    ("reject", "Reject", "Reject and close the instance", True),
    ("forward_to_manager", "Forward to Manager", "Forward to manager for review", False),
    ("forward_to_account_manager", "Forward to Account Manager", "Forward to account manager", False),
    ("settle_cash", "Settle by Cash", "Mark as settled by cash and close", True),
]


class Command(BaseCommand):
    help = "Create common ApprovalActionType rows and backfill existing ApprovalAction entries."

    def handle(self, *args, **options):
        created = []
        for slug, label, desc, ends_flow in COMMON_ACTIONS:
            obj, was_created = ApprovalActionType.objects.get_or_create(
                slug=slug,
                defaults={"label": label, "description": desc, "ends_flow": ends_flow},
            )
            created.append((slug, was_created))

        self.stdout.write("Action types ensured:")
        for slug, was_created in created:
            self.stdout.write(f" - {slug}: {'created' if was_created else 'already existed'}")

        # Backfill existing ApprovalAction rows that don't have action_type:
        to_backfill = ApprovalAction.objects.filter(action_type__isnull=True)
        cnt_all = to_backfill.count()
        self.stdout.write(f"Found {cnt_all} ApprovalAction rows needing backfill...")

        mapped = 0
        with transaction.atomic():
            for act in to_backfill:
                # Heuristic: use approved boolean
                if act.approved is True:
                    slug = "approve"
                elif act.approved is False:
                    slug = "reject"
                else:
                    slug = None

                if slug:
                    try:
                        at = ApprovalActionType.objects.get(slug=slug)
                        act.action_type = at
                        act.save(update_fields=["action_type"])
                        mapped += 1
                    except ApprovalActionType.DoesNotExist:
                        # should not happen
                        continue

        self.stdout.write(f"Backfilled {mapped} of {cnt_all} rows (mapped by approved boolean).")
        if mapped < cnt_all:
            self.stdout.write("Some rows left unmapped; please inspect those in admin and set action_type manually.")
