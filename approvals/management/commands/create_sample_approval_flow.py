# approvals/management/commands/create_sample_approval_flow.py
from django.core.management.base import BaseCommand
from approvals.models import ApprovalActionType, ApprovalFlow, ApprovalStep
from approvals.services import create_instance_for
from expenses.models import Expense
from django.db import transaction

class Command(BaseCommand):
    help = "Create a sample approval flow, steps, action types and create an instance for the first Expense."

    def handle(self, *args, **options):
        with transaction.atomic():
            # Create canonical action types
            created = []
            for slug, label, ends in [
                ("approve", "Approve", True),
                ("reject", "Reject", True),
                ("forward_to_manager", "Forward to Manager", False),
                ("forward_to_account_manager", "Forward to Account Manager", False),
                ("settle_cash", "Settle by Cash", True),
            ]:
                obj, was_created = ApprovalActionType.objects.get_or_create(
                    slug=slug,
                    defaults={"label": label, "description": label, "ends_flow": ends},
                )
                if was_created:
                    created.append(obj.slug)

            self.stdout.write(self.style.SUCCESS(f"Action types ensured. Created: {created or 'none (already existed)'}"))

            # Create or get a sample flow
            flow, fc = ApprovalFlow.objects.get_or_create(
                slug="sample-expense-flow",
                defaults={"name": "Sample Expense Flow", "description": "Flow created for testing"}
            )
            if fc:
                self.stdout.write(self.style.SUCCESS(f"Created flow {flow.slug}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Using existing flow {flow.slug}"))

            # Create steps (idempotent)
            # Step 0: Manager  (selector_type='role', selector_value='Manager')
            step0, s0c = ApprovalStep.objects.get_or_create(
                flow=flow, order=0,
                defaults={"selector_type": "role", "selector_value": "Manager", "auto_approve": False, "allow_reject": True}
            )
            step1, s1c = ApprovalStep.objects.get_or_create(
                flow=flow, order=1,
                defaults={"selector_type": "role", "selector_value": "Accountant", "auto_approve": False, "allow_reject": True}
            )
            step2, s2c = ApprovalStep.objects.get_or_create(
                flow=flow, order=2,
                defaults={"selector_type": "role", "selector_value": "Account Manager", "auto_approve": False, "allow_reject": True}
            )

            self.stdout.write(self.style.SUCCESS(f"Steps ensured for flow: {[s.order for s in flow.steps.all()]}"))

            # Assign allowed actions for each step (use canonical slugs)
            approve_tt = ApprovalActionType.objects.get(slug="approve")
            reject_tt = ApprovalActionType.objects.get(slug="reject")
            fwd_mgr_tt = ApprovalActionType.objects.get(slug="forward_to_manager")
            fwd_am_tt = ApprovalActionType.objects.get(slug="forward_to_account_manager")
            settle_tt = ApprovalActionType.objects.get(slug="settle_cash")

            # Manager step: can forward or reject (or approve if you want)
            step0.allowed_actions.set([fwd_mgr_tt, reject_tt, approve_tt])
            step1.allowed_actions.set([fwd_am_tt, reject_tt, approve_tt])
            # Account Manager (final): can approve or reject or settle
            step2.allowed_actions.set([approve_tt, reject_tt, settle_tt])

            self.stdout.write(self.style.SUCCESS("Assigned allowed actions to steps."))

            # Create an instance for the first Expense (if present)
            expense = Expense.objects.first()
            if not expense:
                self.stdout.write(self.style.WARNING("No Expense found in DB to create an instance for."))
                return

            # Check if an instance already exists for this object
            from approvals.models import ApprovalInstance
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(expense)
            existing = ApprovalInstance.objects.filter(content_type=ct, object_id=expense.id).first()
            if existing:
                self.stdout.write(self.style.NOTICE(f"ApprovalInstance already exists for Expense id {expense.id} (id={existing.id})"))
                return

            inst = create_instance_for(expense, flow)
            self.stdout.write(self.style.SUCCESS(f"Created ApprovalInstance id={inst.id} for Expense id={expense.id}"))
