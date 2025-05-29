# services/project_skill_service.py
def save_required_skills(project, selected_skills):
    from ..models import ProjectRequiredSkill
    if not project or not selected_skills:
        return

    # Clean old
    project.required_skills.all().delete()

    for skill in selected_skills:
        main_skill_id = skill.get('main_skill_id')
        subskill_id = skill.get('subskill_id')
        if main_skill_id and subskill_id:
            ProjectRequiredSkill.objects.create(
                project=project,
                main_skill_id=main_skill_id,
                subskill_id=subskill_id
            )
