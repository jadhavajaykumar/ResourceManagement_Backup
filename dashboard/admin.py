from django.contrib import admin
from .models import ModuleAccess


@admin.register(ModuleAccess)
class ModuleAccessAdmin(admin.ModelAdmin):
    list_display = ('group', 'module')