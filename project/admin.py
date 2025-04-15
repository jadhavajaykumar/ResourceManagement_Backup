
# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import CustomUser
from django.utils.translation import gettext_lazy as _
from .models import Project, Task



from django.contrib import admin
from .models import Project, Task, Subtask  # Updated models only

admin.site.register(Project)
admin.site.register(Task)
admin.site.register(Subtask)
#admin.site.register(TaskAssignment)  # Add clearly



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
