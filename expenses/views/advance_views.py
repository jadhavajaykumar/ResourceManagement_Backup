from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from expenses.forms import AdvanceRequestForm
from expenses.models import AdvanceRequest


@login_required
def delete_advance(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, id=advance_id, employee=request.user.employeeprofile)

    if advance.status == "Submitted" and advance.current_stage == "MANAGER":
        advance.delete()
        messages.success(request, "Advance request deleted successfully.")
    else:
        messages.error(request, "Only submitted advances at Manager stage can be deleted.")

    return redirect('expenses:unified-expense-dashboard')


@login_required
def edit_advance(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, id=advance_id, employee=request.user.employeeprofile)

    if request.method == "POST":
        form = AdvanceRequestForm(request.POST, instance=advance)
        if form.is_valid():
            form.save()
            messages.success(request, "Advance request updated successfully.")
            return redirect('expenses:unified-expense-dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
            return redirect('expenses:unified-expense-dashboard')

    return redirect('expenses:unified-expense-dashboard')


@login_required
def edit_advance_json(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, pk=advance_id, employee__user=request.user)

    # 🔒 Allow edit only if still at MANAGER stage + Submitted
    if not (advance.status == "Submitted" and advance.current_stage == "MANAGER"):
        return JsonResponse({"error": "Editing is allowed only at Manager stage while Submitted."}, status=403)

    form = AdvanceRequestForm(instance=advance, employee=request.user.employeeprofile)
    form_html = render_to_string(
        "expenses/advance_form_wrapper.html",
        {"form": form, "editing": True, "advance": advance},
        request=request
    )
    return JsonResponse({"form_html": form_html})