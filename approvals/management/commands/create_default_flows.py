# File: approvals/management/commands/create_default_flows.py
from django.core.management.base import BaseCommand
from approvals.models import ApprovalFlow, ApprovalStep, ApprovalActionType


class Command(BaseCommand):
    help = "Create default approval flows and action types for expenses"

    def handle(self, *args, **options):
        # Create action types
        approve_at, _ = ApprovalActionType.objects.get_or_create(slug="approve", defaults={"label": "Approve", "ends_flow": True})
        reject_at, _ = ApprovalActionType.objects.get_or_create(slug="reject", defaults={"label": "Reject", "ends_flow": True})

        # Employee flow: Accountant -> Reporting Manager -> Account Manager
        ef, created = ApprovalFlow.objects.get_or_create(name="Expense - employee", defaults={"slug": "expense-employee"})
        if created or not ef.steps.exists():
            ApprovalStep.objects.filter(flow=ef).delete()
            ApprovalStep.objects.create(flow=ef, order=0, selector_type="role", selector_value="accountant")
            ApprovalStep.objects.create(flow=ef, order=1, selector_type="role", selector_value="reporting_manager")
            ApprovalStep.objects.create(flow=ef, order=2, selector_type="role", selector_value="account_manager")
            self.stdout.write(self.style.SUCCESS(f"Created/updated flow: {ef.name}"))

        # Accountant flow: Account Manager only
        af, created = ApprovalFlow.objects.get_or_create(name="Expense - accountant", defaults={"slug": "expense-accountant"})
        if created or not af.steps.exists():
            ApprovalStep.objects.filter(flow=af).delete()
            ApprovalStep.objects.create(flow=af, order=0, selector_type="role", selector_value="account_manager")
            self.stdout.write(self.style.SUCCESS(f"Created/updated flow: {af.name}"))

        self.stdout.write(self.style.SUCCESS("Default flows and action types ensured."))
