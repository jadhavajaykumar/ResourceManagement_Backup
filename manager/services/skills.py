# manager/services/skills.py

from manager.models import EmployeeSkill

def get_employee_skills(employee_profile):
    """
    Fetches EmployeeSkill objects for a given employee profile,
    and annotates them with a 'percentage' for progress bars.
    """
    skills = EmployeeSkill.objects.filter(employee=employee_profile)

    for skill in skills:
        try:
            skill.percentage = int((skill.rating / 4.0) * 100)
        except:
            skill.percentage = 0

    return skills
