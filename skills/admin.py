# skills/admin.py
from django.contrib import admin
from .models import MainSkill, SubSkill, EmployeeSkill, SkillQuestion, EmployeeAnswer

@admin.register(MainSkill)
class MainSkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = []

@admin.register(SubSkill)
class SubSkillAdmin(admin.ModelAdmin):
    list_display = ('name','main_skill')
    list_filter = ('main_skill',)

@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ('employee','main_skill','subskill','rating')
    list_filter = ('main_skill',)

@admin.register(SkillQuestion)
class SkillQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'main_skill', 'subskill', 'order', 'text_short')
    list_filter = ('main_skill', 'subskill',)
    search_fields = ('text',)
    ordering = ('main_skill', 'subskill', 'order')
    def text_short(self, obj):
        return (obj.text[:70] + '...') if len(obj.text) > 70 else obj.text
    text_short.short_description = 'Question'

@admin.register(EmployeeAnswer)
class EmployeeAnswerAdmin(admin.ModelAdmin):
    list_display = ('employee','question','manager_rating','updated_at')
    list_filter = ('question__main_skill', 'question__subskill', 'manager_rating')
    search_fields = ('employee__user__first_name','employee__user__last_name','answer_text')
