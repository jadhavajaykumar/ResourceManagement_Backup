from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django import forms
from django.urls import path
from django.shortcuts import render
from django.contrib import messages
from .models import EmployeeProfile
from .forms import EmployeeProfileForm
from accounts.models import CustomUser

# Custom User Admin with Inline Profile
class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    form = EmployeeProfileForm
    can_delete = False
    verbose_name_plural = 'Employee Profile'
    fk_name = 'user'
    extra = 0

class CustomUserAdmin(UserAdmin):
    inlines = (EmployeeProfileInline,)
    list_display = ('username', 'email', 'get_role', 'is_staff', 'is_active')
    list_select_related = ('employeeprofile',)
    search_fields = ('username', 'email', 'employee_profile__role')
    #list_filter = ('is_staff', 'is_active', 'employee_profile__role')
    list_filter = ('is_staff', 'is_active', 'employeeprofile__role')
    
    def get_role(self, instance):
        return instance.employee_profile.role if hasattr(instance, 'employee_profile') else '-'
    get_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

# Employee Profile Admin
@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    form = EmployeeProfileForm
    list_display = ('user', 'role', 'department', 'employment_type')
    list_filter = ('role', 'department', 'employment_type')
    search_fields = ('user__username', 'user__email', 'role', 'employee_id')
    raw_id_fields = ('user', 'reporting_manager')
    readonly_fields = ('employee_id',)
    actions = ['make_manager', 'make_employee', 'activate_users', 'deactivate_users']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request  # Pass request to the form for permission checks
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('timesheet.can_approve'):
            qs = qs.exclude(role='Admin')
        return qs

    def has_change_permission(self, request, obj=None):
        if obj and obj.role == 'Admin' and not request.user.has_perm('timesheet.can_approve'):
            return False
        return super().has_change_permission(request, obj)

    # Admin Actions
    def make_manager(self, request, queryset):
        updated = queryset.exclude(role='Admin').update(role='Manager')
        self.message_user(request, f"{updated} users promoted to Manager")
    make_manager.short_description = "Promote selected to Manager"

    def make_employee(self, request, queryset):
        updated = queryset.exclude(role='Admin').update(role='Employee')
        self.message_user(request, f"{updated} users demoted to Employee")
    make_employee.short_description = "Demote selected to Employee"

    def activate_users(self, request, queryset):
        User = get_user_model()
        User.objects.filter(id__in=queryset.values('user')).update(is_active=True)
        self.message_user(request, f"{queryset.count()} users activated")
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        User = get_user_model()
        User.objects.filter(id__in=queryset.values('user')).update(is_active=False)
        self.message_user(request, f"{queryset.count()} users deactivated")
    deactivate_users.short_description = "Deactivate selected users"

    # Custom Views
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('role-stats/', self.admin_site.admin_view(self.role_stats_view), name='role_stats'),
        ]
        return custom_urls + urls

    def role_stats_view(self, request):
        if not request.user.has_perm('timesheet.can_approve'):
            messages.error(request, "You don't have permission to view this page")
            return redirect('admin:index')
            
        stats = EmployeeProfile.objects.all().values('role').annotate(count=models.Count('role'))
        context = {
            **self.admin_site.each_context(request),
            'title': 'Role Statistics',
            'stats': stats,
        }
        return render(request, 'admin/role_stats.html', context)

# Unregister and re-register User model
admin.site.unregister(CustomUser)
admin.site.register(CustomUser, CustomUserAdmin)

from django.contrib import admin
from .models import LeaveBalance

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'c_off', 'updated_at')
    search_fields = ('employee__user__first_name', 'employee__user__email')
