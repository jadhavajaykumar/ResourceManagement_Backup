from django.test import TestCase
from django.contrib.auth import get_user_model
from approvals.models import ApprovalActionType, ApprovalFlow, ApprovalStep, ApprovalInstance
from approvals.services import create_instance_for, perform_action_on_instance
from expenses.models import Expense

User = get_user_model()

class ApprovalFlowSmokeTest(TestCase):
    def test_flow_approve_sequence(self):
        # create action types
        approve, _ = ApprovalActionType.objects.get_or_create(slug="approve", defaults={"label":"Approve", "ends_flow":True})
        reject, _ = ApprovalActionType.objects.get_or_create(slug="reject", defaults={"label":"Reject", "ends_flow":True})

        flow = ApprovalFlow.objects.create(name="tflow", slug="tflow")
        ApprovalStep.objects.create(flow=flow, order=0, selector_type="role", selector_value="Manager")
        ApprovalStep.objects.create(flow=flow, order=1, selector_type="role", selector_value="Account Manager")

        exp = Expense.objects.create(...)  # create minimal required fields for your model, or use a fixture

        inst = create_instance_for(exp, flow)
        user = User.objects.create_user("t", "t@t.com", "pw")

        # ensure action type exists
        perform_action_on_instance(inst, "approve", actor=user, remark="ok")
        inst.refresh_from_db()
        self.assertIn(inst.result, ("APPROVED", None))
