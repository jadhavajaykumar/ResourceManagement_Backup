from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from accounts.models import CustomUser
from employee.models import EmployeeProfile
from employee.forms import EmployeeProfileForm


@login_required
def employee_list(request):
    employees = EmployeeProfile.objects.select_related('user').all()
    return render(request, 'employee/employee_list.html', {'employees': employees})


@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeProfileForm(request.POST)
        user_id = form.data.get('user')
        if user_id:
            form.instance.user = CustomUser.objects.filter(pk=user_id).first()
        if form.is_valid():
            form.save()
            return redirect('employee:employee-list')
    else:
        form = EmployeeProfileForm()
    return render(request, 'employee/employee_form.html', {'form': form})