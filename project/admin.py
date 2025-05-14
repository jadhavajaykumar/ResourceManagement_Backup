
# Register your models here.
from django.contrib import admin

# ✅ Correct (new)
from .models import Project, Task, Subtask, ProjectExpensePolicy, CountryDARate

from django.contrib.auth.admin import UserAdmin
from accounts.models import CustomUser
from django.utils.translation import gettext_lazy as _




#admin.site.register(Project)
#admin.site.register(Task)
#admin.site.register(Subtask)
#admin.site.register(TaskAssignment)  # Add clearly

#admin.site.register(ProjectExpensePolicy)
#admin.site.register(CountryDASettings)



@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Fields shown in the admin form when adding/editing users
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "middle_name", "last_name", "email")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    # Fields shown when creating a user via "Add user" form
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "first_name", "middle_name", "last_name", "password1", "password2"),
        }),
    )
    list_display = ("username", "email", "first_name", "middle_name", "last_name", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'customer_name', 'project_type', 'location', 'status']
    list_filter = ['project_type', 'location', 'status']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'due_date', 'progress']

@admin.register(Subtask)
class SubtaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'task', 'completed']

@admin.register(ProjectExpensePolicy)
class ProjectExpensePolicyAdmin(admin.ModelAdmin):
    list_display = ['project', 'allow_transport', 'allow_safety_shoes']

@admin.register(CountryDARate)
class CountryDARateAdmin(admin.ModelAdmin):
    list_display = ['country', 'currency', 'da_rate_per_hour', 'extra_hour_rate']
    search_fields = ['country', 'currency']