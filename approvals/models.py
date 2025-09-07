# approvals/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class ApprovalType(models.Model):
    code = models.CharField(max_length=50, unique=True)   # e.g., "EXPENSE"
    name = models.CharField(max_length=100)              # e.g., "Expense Approval"

    def __str__(self):
        return self.name


class ApprovalFlow(models.Model):
    name = models.CharField(max_length=100)              # e.g., "Default Expense Flow"
    approval_type = models.ForeignKey(ApprovalType, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.approval_type.code})"


class ApprovalStep(models.Model):
    flow = models.ForeignKey(ApprovalFlow, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    role = models.CharField(max_length=50, blank=True, null=True)  # "Manager", "Account Manager"
    group = models.ForeignKey("auth.Group", on_delete=models.SET_NULL, null=True, blank=True)
    use_reporting_manager = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.flow.name} - Step {self.order}"


class ApprovalInstance(models.Model):
    flow = models.ForeignKey(ApprovalFlow, on_delete=models.CASCADE)
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_content_type", "target_object_id")

    current_step = models.PositiveIntegerField(default=1)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.flow.name} for {self.target}"


class ApprovalAction(models.Model):
    instance = models.ForeignKey(ApprovalInstance, on_delete=models.CASCADE, related_name="actions")
    step = models.PositiveIntegerField()
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[("Approved", "Approved"), ("Rejected", "Rejected")])
    remark = models.TextField(blank=True)
    acted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Step {self.step} by {self.approver} → {self.status}"
