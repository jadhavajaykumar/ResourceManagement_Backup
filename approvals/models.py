# approvals/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

# Keep your original model shapes (ApprovalFlow, ApprovalStep, ApprovalInstance, ApprovalActionType, ApprovalAction)
# but add working methods for resolution and applying actions.

class ApprovalFlow(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ApprovalStep(models.Model):
    flow = models.ForeignKey(ApprovalFlow, related_name="steps", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()
    selector_type = models.CharField(
        max_length=20,
        choices=(("role", "Role"), ("group", "Group"), ("user", "User")),
    )
    selector_value = models.CharField(
        max_length=200, help_text="Role name or Group name or User id (int)"
    )
    auto_approve = models.BooleanField(default=False)
    allow_reject = models.BooleanField(default=True)

    allowed_actions = models.ManyToManyField("ApprovalActionType", blank=True)

    class Meta:
        ordering = ("order",)
        unique_together = ("flow", "order")

    def __str__(self):
        return f"{self.flow.name} step {self.order} -> {self.selector_type}:{self.selector_value}"


class ApprovalInstance(models.Model):
    flow = models.ForeignKey(ApprovalFlow, on_delete=models.PROTECT)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(auto_now_add=True)
    current_step_index = models.PositiveIntegerField(default=0)
    finished = models.BooleanField(default=False)
    result = models.CharField(max_length=20, blank=True, null=True)  # APPROVED, REJECTED

    def current_step(self):
        steps = list(self.flow.steps.all().order_by('order'))
        if self.current_step_index < len(steps):
            return steps[self.current_step_index]
        return None

    def get_ordered_steps(self):
        return list(self.flow.steps.all().order_by('order'))

    def start(self):
        """Initialize the instance: set to first step and if step is auto_approve, apply it."""
        if self.finished:
            return
        steps = self.get_ordered_steps()
        if not steps:
            # no steps => immediate approve
            self.finished = True
            self.result = "APPROVED"
            self.current_step_index = 0
            self.save(update_fields=['finished', 'result', 'current_step_index'])
            self._on_finalized(approved=True)
            return

        self.current_step_index = 0
        self.finished = False
        self.result = None
        self.save(update_fields=['current_step_index', 'finished', 'result'])

        # if first step is auto_approve, apply programmatically
        step = self.current_step()
        if step and step.auto_approve:
            # create an ApprovalAction with a system actor (None) using an 'auto-approve' action type if exists
            opt = ApprovalActionType.objects.filter(slug__iexact='approve').first()
            if opt:
                ApprovalAction.objects.create(instance=self, step=step, actor=None, action_type=opt, remark="Auto-approved")
            # move to next
            self._advance_after_action(approved=True)

    def _resolve_selector_to_user(self, step):
            """
            Resolve a concrete user for the step or return None.
            Resolution rules (improved):
              - selector_type == 'user' => selector_value is user PK or username
              - selector_type == 'group' => pick first active user in that group
              - selector_type == 'role' => common roles: 'accountant','account_manager','reporting_manager'
                                           reporting_manager tries expense.employee -> .reporting_manager etc.
            This version also attempts to resolve reporting_manager stored as string (email/username).
            """
            from django.contrib.auth import get_user_model
            from django.contrib.auth.models import Group

            User = get_user_model()
            if step.selector_type == 'user':
                v = step.selector_value
                try:
                    uid = int(v)
                    return User.objects.filter(pk=uid).first()
                except Exception:
                    # treat as username or email
                    return User.objects.filter(username=v).first() or User.objects.filter(email__iexact=v).first()

            if step.selector_type == 'group':
                gname = step.selector_value or ""
                try:
                    group = Group.objects.filter(name__iexact=gname).first()
                    if group:
                        return User.objects.filter(groups=group, is_active=True).first()
                except Exception:
                    return None

            if step.selector_type == 'role':
                role = (step.selector_value or '').strip().lower()
                if role in ('accountant', 'accounts'):
                    group = Group.objects.filter(name__icontains='accountant').first()
                    if group:
                        return User.objects.filter(groups=group, is_active=True).first()

                if role in ('account_manager', 'account manager'):
                    group = Group.objects.filter(name__icontains='account manager').first()
                    if group:
                        return User.objects.filter(groups=group, is_active=True).first()

                if role in ('reporting_manager', 'reporting manager', 'manager'):
                    try:
                        obj = self.content_object
                        if hasattr(obj, 'employee'):
                            emp = getattr(obj, 'employee', None)
                            if emp is not None:
                                # Try common attribute names for reporting manager on EmployeeProfile
                                for attr in ('reporting_manager', 'reporting_to', 'manager', 'line_manager'):
                                    if hasattr(emp, attr):
                                        candidate = getattr(emp, attr)
                                        if candidate:
                                            # If candidate is User instance (or EmployeeProfile with .user)
                                            if hasattr(candidate, 'pk') and hasattr(candidate, 'username'):
                                                # candidate looks like a User already
                                                return candidate
                                            if hasattr(candidate, 'user'):
                                                return getattr(candidate, 'user')
                                            # if it's a string (email/username) attempt to resolve
                                            try:
                                                # try integer id
                                                cid = int(candidate)
                                                u = User.objects.filter(pk=cid).first()
                                                if u:
                                                    return u
                                            except Exception:
                                                # try as email or username
                                                u = User.objects.filter(username=candidate).first() or User.objects.filter(email__iexact=candidate).first()
                                                if u:
                                                    return u
                        # Fallback to group 'Manager'
                        group = Group.objects.filter(name__icontains='manager').first()
                        if group:
                            return User.objects.filter(groups=group, is_active=True).first()
                    except Exception:
                        return None

            return None


    def is_actor_allowed(self, actor):
        """
        Return True if `actor` (User instance) is allowed to act on the current step.
        """
        if self.finished or actor is None:
            return False
        step = self.current_step()
        if not step:
            return False

        # if step.allowed_actions is empty -> any action-type is allowed (subject to allow_reject)
        # resolve the step to a specific user if possible
        resolved = self._resolve_selector_to_user(step)
        from django.contrib.auth.models import Group

        # if resolved user found -> actor must be that user
        if resolved is not None:
            try:
                return actor.pk == resolved.pk
            except Exception:
                return False

        # else fall back: if selector_type == 'group' or 'role', allow group members
        if step.selector_type == 'group' or step.selector_type == 'role':
            try:
                # check groups that match selector_value substring
                return actor.groups.filter(name__icontains=step.selector_value).exists()
            except Exception:
                return False

        return False

    def apply_action(self, actor, action_type_slug, remark=''):
        """
        Apply an action (e.g. 'approve' or 'reject') by an actor.
        action_type_slug must match an ApprovalActionType.slug.
        Returns (ok_bool, message)
        """
        from django.core.exceptions import PermissionDenied

        if self.finished:
            return False, "Instance already finished"

        # check permission
        if not self.is_actor_allowed(actor):
            raise PermissionDenied("User not allowed to act on this step")

        step = self.current_step()
        if step is None:
            return False, "No current step"

        action_type = ApprovalActionType.objects.filter(slug__iexact=action_type_slug).first()
        if not action_type:
            return False, "Unknown action type"

        # If action is a reject and step does not allow reject
        if action_type_slug.lower() in ('reject',) and not step.allow_reject:
            return False, "Reject not allowed on this step"

        # create Action log
        ApprovalAction.objects.create(instance=self, step=step, actor=actor, action_type=action_type, remark=remark)

        # If action_type.ends_flow is True or action is 'reject' -> finalize as rejected/approved accordingly
        if action_type.ends_flow:
            # determine approved vs rejected based on slug
            if action_type_slug.lower() in ('approve', 'approved'):
                self.finished = True
                self.result = "APPROVED"
                self.save(update_fields=['finished', 'result'])
                self._on_finalized(approved=True)
                return True, "Approved and finalized"
            elif action_type_slug.lower() in ('reject', 'rejected'):
                self.finished = True
                self.result = "REJECTED"
                self.save(update_fields=['finished', 'result'])
                self._on_finalized(approved=False)
                return True, "Rejected and finalized"

        # Otherwise advance to next step
        return self._advance_after_action(approved=True)

    def _advance_after_action(self, approved=True):
        """Advance current_step_index or finalize if at last step."""
        steps = self.get_ordered_steps()
        if not steps:
            self.finished = True
            self.result = "APPROVED" if approved else "REJECTED"
            self.save(update_fields=['finished', 'result'])
            self._on_finalized(approved=approved)
            return True, "Finalized (no steps)"

        if self.current_step_index + 1 < len(steps):
            self.current_step_index += 1
            self.save(update_fields=['current_step_index'])
            # If next step is auto-approve, recursively apply
            nxt = self.current_step()
            if nxt and nxt.auto_approve:
                # create an ApprovalAction log for auto-approve if action type exists
                at = ApprovalActionType.objects.filter(slug__iexact='approve').first()
                if at:
                    ApprovalAction.objects.create(instance=self, step=nxt, actor=None, action_type=at, remark='Auto-approved')
                return self._advance_after_action(approved=True)
            return True, "Moved to next step"
        # else finalize
        self.finished = True
        self.result = "APPROVED" if approved else "REJECTED"
        self.save(update_fields=['finished', 'result'])
        self._on_finalized(approved=approved)
        return True, "Finalized (last step)"

    def _on_finalized(self, approved):
        """
        Hook when instance finalizes. Try calling content_object.on_approval_completed(approved, instance)
        otherwise try to update Expense fields if applicable.
        """
        try:
            obj = self.content_object
            hook = getattr(obj, 'on_approval_completed', None)
            if callable(hook):
                hook(approved=approved, approval_instance=self)
                return
            # Fallback: many projects store status/current_stage on the domain model. Try to update
            if hasattr(obj, 'status') or hasattr(obj, 'current_stage'):
                # Map our result to expense status and stage heuristics
                if approved:
                    # If flow name contains 'accountant' and instance.flow.name contains 'Expense - accountant'
                    # then we assume Account Manager handled final settlement -> set Approved/Settled
                    try:
                        if 'accountant' in (self.flow.name or '').lower():
                            obj.status = 'Approved'
                            obj.current_stage = 'ACCOUNT_MANAGER'
                        else:
                            # employee flow final -> APPROVED/SETTLED
                            obj.status = 'Approved'
                            obj.current_stage = 'SETTLED'
                        obj.save()
                    except Exception:
                        pass
                else:
                    try:
                        obj.status = 'Rejected'
                        obj.current_stage = 'REJECTED'
                        obj.save()
                    except Exception:
                        pass
        except Exception:
            # swallow exceptions to avoid blocking approval flow finalization
            pass


class ApprovalActionType(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ends_flow = models.BooleanField(
        default=False,
        help_text="If checked, performing this action typically ends the approval instance (e.g. approve/reject).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Approval Action Type"
        verbose_name_plural = "Approval Action Types"

    def __str__(self):
        return self.label


class ApprovalAction(models.Model):
    instance = models.ForeignKey(ApprovalInstance, related_name="actions", on_delete=models.CASCADE)
    step = models.ForeignKey(ApprovalStep, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    # final state: required FK to canonical action types
    action_type = models.ForeignKey("ApprovalActionType", on_delete=models.PROTECT)

    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.instance} {self.action_type.slug if self.action_type else 'unknown'} by {self.actor}"
