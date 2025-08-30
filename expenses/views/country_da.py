# expenses/views/country_da.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from ..forms import CountryDASettingForm
from ..models import CountryDARate



@login_required
@permission_required('timesheet.can_approve')
def manage_country_da(request):
    form = CountryDASettingForm()
    country_rates = CountryDARate.objects.all().order_by('country')

    if request.method == "POST" and 'add_country' in request.POST:
        form = CountryDASettingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Country DA settings added successfully.")
            return redirect('expenses:manage-country-da')

    return render(request, 'expenses/manage_country_da.html', {
        'form': form,
        'country_rates': country_rates,
        'edit_mode': False,
    })

@login_required
@permission_required('timesheet.can_approve')
def edit_country_da(request, rate_id):
    instance = get_object_or_404(CountryDARate, id=rate_id)
    form = CountryDASettingForm(request.POST or None, instance=instance)
    country_rates = CountryDARate.objects.all().order_by('country')

    if request.method == "POST" and 'update_country' in request.POST:
        if form.is_valid():
            form.save()
            messages.success(request, "Country DA settings updated.")
            return redirect('expenses:manage-country-da')

    return render(request, 'expenses/manage_country_da.html', {
        'form': form,
        'country_rates': country_rates,
        'edit_mode': True,
    })

@login_required
@permission_required('timesheet.can_approve')
def delete_country_da(request, rate_id):
    if request.method == "POST":
        rate = get_object_or_404(CountryDARate, id=rate_id)
        rate.delete()
        messages.success(request, f"{rate.country} removed successfully.")
    return redirect('expenses:manage-country-da')
