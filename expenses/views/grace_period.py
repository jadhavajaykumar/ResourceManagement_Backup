# expenses/views/grace_period.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from ..forms import GracePeriodForm
from ..models import SystemSettings
from accounts.access_control import is_manager_or_admin


@login_required
@user_passes_test(is_manager_or_admin)
def manage_expense_settings(request):
    settings_obj, _ = SystemSettings.objects.get_or_create(id=1)

    if request.method == 'POST':
        form = GracePeriodForm(request.POST, instance=settings_obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(request, "Grace period updated successfully.")
            return redirect('expenses:manage-settings')
    else:
        form = GracePeriodForm(instance=settings_obj)

    return render(request, 'expenses/manage_settings.html', {'form': form})
