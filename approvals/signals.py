# approvals/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
import logging

logger = logging.getLogger(__name__)

from approvals.models import ApprovalFlow, ApprovalInstance

# Heuristic: when an Expense becomes Submitted, create ApprovalInstance
# You can change the status string matching to your project conventions.

@receiver(post_save)
def expense_create_approval(sender, instance, created, **kwargs):
    # avoid reacting to approvals app models
    if sender._meta.app_label == 'approvals':
        return

    # Only target the Expense model specifically (safest)
    if sender.__name__ != 'Expense':
        return

    # Ensure instance has 'status' attribute
    status = getattr(instance, 'status', None)
    if status is None:
        return

    # Only create when status is 'Submitted' (employee submitted)
    # If your app uses different values, adjust accordingly
    if str(status).lower() != 'submitted':
        return

    # avoid creating duplicate ApprovalInstance
    ctype = ContentType.objects.get_for_model(instance.__class__)
    existing = ApprovalInstance.objects.filter(content_type=ctype, object_id=instance.pk).first()
    if existing:
        # already an instance — if unfinished, ignore; if finished but new submission flow required, you can adapt
        return

    # Decide which flow to use:
    # If submitter (instance.employee.user) is in group 'Accountant' choose accountant flow
    user = None
    try:
        user = getattr(instance, 'employee').user
    except Exception:
        user = None

    flow = None
    try:
        if user and user.groups.filter(name__icontains='accountant').exists():
            flow = ApprovalFlow.objects.filter(name__iexact='Expense - accountant',).first()
        if not flow:
            flow = ApprovalFlow.objects.filter(name__iexact='Expense - employee').first()
        if not flow:
            flow = ApprovalFlow.objects.filter().first()
    except Exception as e:
        logger.exception("Error selecting approval flow: %s", e)
        flow = ApprovalFlow.objects.filter().first()

    if not flow:
        logger.warning("No ApprovalFlow found to attach to Expense %s", instance.pk)
        return

    # create instance and start it
    try:
        inst = ApprovalInstance.objects.create(
            flow=flow,
            content_type=ctype,
            object_id=instance.pk,
        )
        inst.start()
    except Exception as e:
        logger.exception("Failed to create/start ApprovalInstance for Expense %s: %s", instance.pk, e)
