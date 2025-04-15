from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser
from employee.models import EmployeeProfile
import logging
from accounts.utils import get_dashboard_redirect_url

logger = logging.getLogger(__name__)

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Ensure profile exists
            from employee.models import EmployeeProfile
            EmployeeProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'Manager' if user.is_staff else 'Employee'}
            )
            
            return redirect(get_dashboard_redirect_url(user))
            
    return render(request, 'accounts/login.html')


@login_required
def redirect_to_dashboard(request):
	redirect_url = get_dashboard_redirect_url(request.user)
	return redirect(redirect_url)

@login_required
def change_user_role(request):
    if request.user.role not in ['Admin', 'Manager', 'Director']:
        messages.error(request, "You do not have permission to change user roles.")
        return redirect('employee:employee-dashboard')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        try:
            user = get_object_or_404(CustomUser, id=user_id)
            profile, created = EmployeeProfile.objects.get_or_create(user=user)
            old_role = profile.role
            if new_role in dict(CustomUser.ROLES):
                profile.role = new_role
                profile.save()
                messages.success(request, f"Role for {user.get_full_name()} updated from {old_role} to {new_role}.")
                logger.info(f"User {request.user.username} changed {user.username}'s role from {old_role} to {new_role}")
            else:
                messages.error(request, "Invalid role selected.")
        except Exception as e:
            messages.error(request, f"Error updating role: {str(e)}")
            logger.error(f"Error changing role for user {user_id}: {str(e)}")
        return redirect('accounts:change-user-role')
    users = CustomUser.objects.all().order_by('username')
    context = {'users': users, 'roles': CustomUser.ROLES}
    return render(request, 'accounts/change_user_role.html', context)