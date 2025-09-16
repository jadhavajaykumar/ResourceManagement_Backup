# approvals/services.py
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from typing import Optional

from .models import ApprovalInstance, ApprovalActionType


def create_instance_for(obj, flow) -> ApprovalInstance:
    """
    Create an ApprovalInstance for obj bound to the provided flow.
    """
    ct = ContentType.objects.get_for_model(obj.__class__)
    inst = ApprovalInstance.objects.create(flow=flow, content_type=ct, object_id=getattr(obj, "pk", None))
    return inst


@transaction.atomic
def perform_action_on_instance(inst: ApprovalInstance, action_slug: str, actor=None, remark: str = "") -> ApprovalInstance:
    """
    Perform the named action on the approval instance by `actor`.
    Delegates to instance.apply_action which performs logging, state changes and finalization hooks.
    Raises PermissionDenied when actor is not allowed, ValueError for invalid args.
    """
    if inst is None:
        raise ValueError("inst is required")

    if actor is None:
        raise ValueError("actor is required")

    # Basic validation for action type existence
    at = ApprovalActionType.objects.filter(slug__iexact=action_slug).first()
    if not at:
        raise ValueError(f"Unknown action slug: {action_slug}")

    # Enforce actor permission (consistent with UI)
    if not inst.is_actor_allowed(actor):
        raise PermissionDenied("Actor is not allowed to perform this action on the current step")

    # Delegate to the model method (centralises audit, advance, finalization)
    ok, msg = inst.apply_action(actor, action_slug, remark=remark)

    # refresh from DB to reflect side-effects
    inst.refresh_from_db()

    return inst
