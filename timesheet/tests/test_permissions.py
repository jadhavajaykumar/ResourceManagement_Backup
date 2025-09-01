from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from employee.models import EmployeeProfile


class PermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="emp", password="pw")
        EmployeeProfile.objects.create(user=self.user, role="Employee")
        self.client.login(username="emp", password="pw")

    def test_comp_off_approval_requires_permission(self):
        response = self.client.get(reverse("timesheet:comp-off-approvals"))
        self.assertEqual(response.status_code, 302)

    def test_assign_task_requires_permission(self):
        response = self.client.get(reverse("project:assign-task"))
        self.assertEqual(response.status_code, 302)