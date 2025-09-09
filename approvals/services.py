# approvals/services.py
from django.contrib.contenttypes.models import ContentType
from .models import ApprovalInstance, ApprovalAction, ApprovalActionType
from django.db import transaction

def create_instance_for(obj, flow):
    ct = ContentType.objects.get_for_model(obj)
    inst = ApprovalInstance.objects.create(flow=flow, content_type=ct, object_id=obj.id)
    return inst


@transaction.atomic
def perform_action_on_instance(inst, action_slug, actor=None, remark=""):
    """
    Record an ApprovalAction on `inst` using canonical action slug.
    Raises ValueError if action type is unknown or the instance has no current step.
    Advances the instance or finishes it according to the action type.
    """
    if inst is None:
        raise ValueError("inst is required")

    action_type = ApprovalActionType.objects.filter(slug=action_slug).first()
    if not action_type:
        raise ValueError(f"Unknown action slug: {action_slug}")

    # Ensure we have a valid current step
    current_step = inst.current_step()
    if current_step is None:
        # Defensive: don't try to create ApprovalAction with step=None
        raise ValueError(
            "Approval instance has no current step. "
            "Ensure the associated ApprovalFlow has ApprovalStep rows and the instance.current_step_index is valid."
        )

    # create audit record
    ApprovalAction.objects.create(
        instance=inst,
        step=current_step,
        actor=actor,
        action_type=action_type,
        remark=remark or "",
    )

    # If this action ends the flow, mark finished/result appropriately
    if action_type.ends_flow:
        inst.finished = True
        if action_type.slug == "approve":
            inst.result = "APPROVED"
        elif action_type.slug == "reject":
            inst.result = "REJECTED"
        else:
            inst.result = action_type.slug.upper()
        inst.save(update_fields=["finished", "result"])
        return inst

    # Otherwise advance sequentially
    inst.current_step_index = inst.current_step_index + 1
    # if we moved beyond last step, finish as approved
    if inst.current_step() is None:
        inst.finished = True
        inst.result = "APPROVED"
    inst.save(update_fields=["current_step_index", "finished", "result"])
    return inst
