# skills/admin.py
from django.contrib import admin
from .models import (
    MainSkill, SubSkill, EmployeeSkill, SkillQuestion, EmployeeAnswer,
    SkillCategory, SkillMatrix, SkillMatrixRow, TaskAssignment
)

@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    search_fields = ('name',)

@admin.register(MainSkill)
class MainSkillAdmin(admin.ModelAdmin):
    # Keep a small, safe list_display that won't error if optional fields are absent.
    list_display = ('name', 'category')
    search_fields = ('name',)
    list_filter = ('category',)

@admin.register(SubSkill)
class SubSkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'main_skill')
    list_filter = ('main_skill',)
    search_fields = ('name',)

@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ('employee', 'main_skill', 'subskill', 'effective_rating_display', 'years_experience', 'certified')
    list_filter = ('main_skill', 'certified')
    search_fields = ('employee__user__first_name', 'employee__user__last_name', 'main_skill__name', 'subskill__name')

    def effective_rating_display(self, obj):
        # show the effective rating (proficiency if present else legacy rating)
        try:
            return obj.effective_rating
        except Exception:
            # fallback if the attribute is missing for any reason
            return getattr(obj, 'rating', None)
    effective_rating_display.short_description = 'Rating'

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
    list_display = ('employee', 'question', 'manager_rating', 'updated_at')
    list_filter = ('question__main_skill', 'question__subskill', 'manager_rating')
    search_fields = ('employee__user__first_name','employee__user__last_name','answer_text')

class SkillMatrixRowInline(admin.TabularInline):
    model = SkillMatrixRow
    extra = 1

@admin.register(SkillMatrix)
class SkillMatrixAdmin(admin.ModelAdmin):
    list_display = ('name',)
    inlines = [SkillMatrixRowInline]

@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'project', 'task', 'assigned_date')
    list_filter = ('assigned_date',)
