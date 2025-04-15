from django.contrib import admin
from .models import MainSkill, SubSkill

class SubSkillInline(admin.TabularInline):
    model = SubSkill
    extra = 1

@admin.register(MainSkill)
class MainSkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    inlines = [SubSkillInline]

@admin.register(SubSkill)
class SubSkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'main_skill')
    list_filter = ('main_skill',)
