from django.urls import path
from .views import (
    assign_skills,
    my_skills,
    load_subskills,
    export_skill_matrix,
    get_employee_skill_data,
    edit_skill_assignment,
    evaluate_skill_view,
    save_evaluation,
    answer_skill_questions,
    skill_overview,
)

app_name = 'skills'

urlpatterns = [
    path('assign/', assign_skills, name='assign-skills'),
    path('my-skills/', my_skills, name='my-skills'),
    path('ajax/load-subskills/', load_subskills, name='ajax-load-subskills'),
    path('export/', export_skill_matrix, name='export-skill-matrix'),
    path('ajax/get-employee-skill-data/', get_employee_skill_data, name='get-employee-skill-data'),
    path('ajax/edit-skill-assignment/', edit_skill_assignment, name='edit-skill-assignment'),

    # Answering (employee) - subskill optional
    path('answer/<int:main_skill_id>/', answer_skill_questions, name='answer-skill-questions'),
    path('answer/<int:main_skill_id>/<int:subskill_id>/', answer_skill_questions, name='answer-skill-questions-sub'),

    # Evaluation (manager) - subskill optional
    path('evaluate/<int:employee_id>/<int:main_skill_id>/', evaluate_skill_view, name='evaluate-skill'),
    path('evaluate/<int:employee_id>/<int:main_skill_id>/<int:subskill_id>/', evaluate_skill_view, name='evaluate-skill-sub'),
    path('evaluate/<int:employee_id>/<int:main_skill_id>/save/', save_evaluation, name='save-evaluation'),
    path('overview/', skill_overview, name='overview'),
]
