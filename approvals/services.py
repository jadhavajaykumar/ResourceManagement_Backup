# approvals/services.py
from django.contrib.contenttypes.models import ContentType
from .models import ApprovalInstance, ApprovalAction, ApprovalStep


def start_approval_flow(obj, flow):
    """Start an approval instance for given object (Expense in our case)."""
    ctype = ContentType.objects.get_for_model(obj)
    instance = ApprovalInstance.objects.create(
        flow=flow,
        target_content_type=ctype,
        target_object_id=obj.id,
        current_step=1,
    )
    return instance


def get_current_approvers(instance):
    """Return list of User objects who can approve at current step."""
    step = instance.flow.steps.filter(order=instance.current_step).first()
    if not step:
        return []

    target = instance.target
    approvers = []

    # Reporting Manager
    if step.use_reporting_manager and hasattr(target, "employee"):
        if target.employee.reporting_manager:
            approvers.append(target.employee.reporting_manager)

    # Group
    if step.group:
        approvers.extend(step.group.user_set.all())

    # Role (from EmployeeProfile)
    if step.role:
        qs = getattr(target.employee, "employeeprofile", None)
        if qs and qs.role == step.role:
            approvers.append(target.employee.user)

    return list(set(approvers))


def advance_flow(instance, approver, remark=""):
    """Approve and move to next step."""
    step = instance.current_step
    ApprovalAction.objects.create(
        instance=instance, step=step, approver=approver, status="Approved", remark=remark
    )

    next_step = instance.flow.steps.filter(order__gt=step).order_by("order").first()
    if next_step:
        instance.current_step = next_step.order
        instance.save()
    else:
        instance.is_completed = True
        instance.save()
        # Update target object
        target = instance.target
        target.status = "Approved"
        target.save()


def reject_flow(instance, approver, remark=""):
    """Reject and stop flow."""
    step = instance.current_step
    ApprovalAction.objects.create(
        instance=instance, step=step, approver=approver, status="Rejected", remark=remark
    )

    instance.is_completed = True
    instance.save()
    # Update target object
    target = instance.target
    target.status = "Rejected"
    target.save()
