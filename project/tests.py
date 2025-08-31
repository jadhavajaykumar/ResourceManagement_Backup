from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission


class ProjectAccessTests(TestCase):
    def setUp(self):
        self.url = reverse("project:project-dashboard")
        User = get_user_model()

        # Regular employee without special permissions
        self.employee = User.objects.create_user(
            username="employee", password="pass1234"
        )

        # Manager with timesheet approval permission
        self.manager = User.objects.create_user(
            username="manager", password="pass1234"
        )
        approve_perm = Permission.objects.get(codename="can_approve")
        self.manager.user_permissions.add(approve_perm)

        # Director via group membership
        self.director = User.objects.create_user(
            username="director", password="pass1234"
        )
        director_group = Group.objects.create(name="Director")
        self.director.groups.add(director_group)

        # Staff/admin user
        self.admin = User.objects.create_user(
            username="admin", password="pass1234", is_staff=True
        )

    def test_manager_can_access_dashboard(self):
        self.client.login(username="manager", password="pass1234")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_director_can_access_dashboard(self):
        self.client.login(username="director", password="pass1234")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_dashboard(self):
        self.client.login(username="admin", password="pass1234")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_access_dashboard(self):
        self.client.login(username="employee", password="pass1234")
        response = self.client.get(self.url)
        # Should redirect to login page due to failed permission test
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

# Create your tests here.
