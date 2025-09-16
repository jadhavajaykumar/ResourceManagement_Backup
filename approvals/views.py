# File: approvals/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views import View
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from .models import ApprovalInstance


class MyPendingApprovalsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        qs = ApprovalInstance.objects.filter(finished=False).select_related("flow")
        result = []
        for inst in qs:
            if inst.is_actor_allowed(user):
                step = inst.current_step()
                result.append(
                    {
                        "id": inst.pk,
                        "object": str(inst.content_object),
                        "flow": inst.flow.name,
                        "current_step": step and f"{step.selector_type}:{step.selector_value}",
                        "created_at": inst.created_at.isoformat(),
                    }
                )
        return JsonResponse(result, safe=False)


class ApproveInstanceView(LoginRequiredMixin, View):
    def post(self, request, instance_id, *args, **kwargs):
        inst = get_object_or_404(ApprovalInstance, pk=instance_id)
        user = request.user
        action = request.POST.get("action")
        remark = request.POST.get("remark", "")
        if not action:
            return HttpResponseBadRequest("missing action")
        try:
            ok, msg = inst.apply_action(user, action_type_slug=action, remark=remark)
            if not ok:
                return HttpResponseForbidden(msg)
        except Exception as exc:
            return HttpResponseForbidden(str(exc))
        return JsonResponse({"ok": True, "status": inst.result, "finished": inst.finished})
