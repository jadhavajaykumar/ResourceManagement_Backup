from django.contrib import admin
from .models import SystemSettings

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('expense_grace_days', 'updated_by', 'updated_at')
