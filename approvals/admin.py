# approvals/admin.py
from django.contrib import admin
from .models import (
    ApprovalFlow,
    ApprovalStep,
    ApprovalInstance,
    ApprovalAction,
    ApprovalActionType,
)


class ApprovalStepInline(admin.TabularInline):
    model = ApprovalStep
    extra = 0


@admin.register(ApprovalFlow)
class ApprovalFlowAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ApprovalStepInline]


@admin.register(ApprovalInstance)
class ApprovalInstanceAdmin(admin.ModelAdmin):
    list_display = ("id", "flow", "object_id", "finished", "result", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ApprovalActionType)
class ApprovalActionTypeAdmin(admin.ModelAdmin):
    list_display = ("slug", "label", "ends_flow", "created_at")
    readonly_fields = ("created_at",)
    prepopulated_fields = {"slug": ("label",)}


@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = ("flow", "order", "selector_type", "selector_value", "auto_approve", "allow_reject")
    filter_horizontal = ("allowed_actions",)


@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ("instance", "step", "actor", "action_type", "created_at")
    readonly_fields = ("created_at",)
    list_filter = ("actor", "action_type")
    search_fields = ("actor__username", "remark")
