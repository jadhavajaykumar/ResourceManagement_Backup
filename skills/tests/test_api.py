# skills/tests/test_api.py
import pytest
from django.urls import reverse
from employee.models import EmployeeProfile
from skills.models import MainSkill, SubSkill, EmployeeSkill

@pytest.mark.django_db
def test_employee_skills_json(client, django_user_model):
    # create user+employee
    user = django_user_model.objects.create_user(username='u1', password='pass', first_name='Test', last_name='User')
    emp = EmployeeProfile.objects.create(user=user)
    ms = MainSkill.objects.create(name='PLC')
    ss = SubSkill.objects.create(main_skill=ms, name='Ladder')
    EmployeeSkill.objects.create(employee=emp, main_skill=ms, subskill=ss, proficiency=80)
    url = reverse('skills:employee-skills-table-json')
    client.force_login(user)
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert 'columns' in data and 'rows' in data
