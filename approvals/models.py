# approvals/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = settings.AUTH_USER_MODEL


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
        steps = list(self.flow.steps.all())
        if self.current_step_index < len(steps):
            return steps[self.current_step_index]
        return None


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
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # final state: required FK to canonical action types
    action_type = models.ForeignKey("ApprovalActionType", on_delete=models.PROTECT)

    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.instance} {self.action_type.slug if self.action_type else 'unknown'} by {self.actor}"
