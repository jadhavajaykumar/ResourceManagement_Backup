from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from datetime import date, time
from decimal import Decimal

from employee.models import EmployeeProfile
from timesheet.models import Timesheet, TimeSlot
from project.models import Project, LocationType
from project.services.da_service import calculate_da
from .forms import ProjectForm
from .models import ProjectStatus, ProjectType, LocationType

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


class ProjectFormTests(TestCase):
    def setUp(self):
        self.status = ProjectStatus.objects.create(name="Active")
        self.project_type = ProjectType.objects.create(name="Service")
        self.location_type = LocationType.objects.create(name="Other")

    def _base_data(self):
        return {
            "name": "Test Project",
            "customer_name": "Acme Corp",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "status_type": self.status.id,
            "project_type": self.project_type.id,
            "location_type": self.location_type.id,
            "rate_type": "Hourly",
            "rate_value": "100",
        }

    def test_customer_end_date_before_start_date(self):
        data = self._base_data()
        data.update({
            "customer_start_date": "2024-05-10",
            "customer_end_date": "2024-05-01",
        })
        form = ProjectForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("customer_end_date", form.errors)

    def test_form_saves_with_valid_customer_dates(self):
        data = self._base_data()
        data.update({
            "customer_start_date": "2024-05-01",
            "customer_end_date": "2024-05-10",
        })
        form = ProjectForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()
        self.assertEqual(str(project.customer_end_date), "2024-05-10")
        
        
        
class ProjectDATests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="emp", password="pass1234")
        self.employee = EmployeeProfile.objects.create(user=self.user)

        self.loc_office = LocationType.objects.create(name="Office")
        self.loc_local = LocationType.objects.create(name="Local")
        self.loc_domestic = LocationType.objects.create(name="Domestic")
        self.loc_international = LocationType.objects.create(name="International")

    def _make_slot(self, project, slot_date=None, hours=8):
        if slot_date is None:
            slot_date = date(2024, 1, 1)
        ts = Timesheet.objects.create(
            employee=self.employee,
            date=slot_date,
            shift_start=time(9, 0),
            shift_end=time(17, 0),
        )
        return TimeSlot.objects.create(
            timesheet=ts,
            project=project,
            employee=self.employee,
            time_from=time(9, 0),
            time_to=time(17, 0),
            hours=hours,
            slot_date=slot_date,
            description="",
        )

    def test_office_da_zero(self):
        project = Project.objects.create(
            name="OfficeProj",
            customer_name="Cust",
            start_date=date(2024, 1, 1),
            status_type=None,
            project_type=None,
            location_type=self.loc_office,
            is_onsite=False,
        )
        slot = self._make_slot(project)
        amount, _ = calculate_da(slot)
        self.assertEqual(amount, Decimal("0.0"))

    def test_local_da_300(self):
        project = Project.objects.create(
            name="LocalProj",
            customer_name="Cust",
            start_date=date(2024, 1, 1),
            status_type=None,
            project_type=None,
            location_type=self.loc_local,
            is_onsite=False,
            da_rate_per_unit=Decimal("300.00"),
        )
        slot = self._make_slot(project)
        amount, _ = calculate_da(slot)
        self.assertEqual(amount, Decimal("300.00"))

    def test_domestic_da_600(self):
        project = Project.objects.create(
            name="DomesticProj",
            customer_name="Cust",
            start_date=date(2024, 1, 1),
            status_type=None,
            project_type=None,
            location_type=self.loc_domestic,
            is_onsite=False,
            da_rate_per_unit=Decimal("600.00"),
        )
        slot = self._make_slot(project)
        amount, _ = calculate_da(slot)
        self.assertEqual(amount, Decimal("600.00"))

    def test_international_onsite_daily(self):
        project = Project.objects.create(
            name="IntlOnsite",
            customer_name="Cust",
            start_date=date(2024, 1, 1),
            status_type=None,
            project_type=None,
            location_type=self.loc_international,
            is_onsite=True,
            da_type="Daily",
            da_rate_per_unit=Decimal("1000.00"),
            off_day_da_rate=Decimal("200.00"),
        )
        slot = self._make_slot(project)
        amount, _ = calculate_da(slot)
        self.assertEqual(amount, Decimal("1000.00"))

    def test_international_onsite_weekend(self):
        project = Project.objects.create(
            name="IntlWeekend",
            customer_name="Cust",
            start_date=date(2024, 1, 1),
            status_type=None,
            project_type=None,
            location_type=self.loc_international,
            is_onsite=True,
            da_type="Daily",
            da_rate_per_unit=Decimal("1000.00"),
            off_day_da_rate=Decimal("200.00"),
        )
        slot = self._make_slot(project, slot_date=date(2024, 1, 6))  # Saturday
        amount, _ = calculate_da(slot)
        self.assertEqual(amount, Decimal("200.00"))

    def test_international_offsite_zero(self):
        project = Project.objects.create(
            name="IntlOffsite",
            customer_name="Cust",
            start_date=date(2024, 1, 1),
            status_type=None,
            project_type=None,
            location_type=self.loc_international,
            is_onsite=False,
            da_type="Daily",
            da_rate_per_unit=Decimal("1000.00"),
            off_day_da_rate=Decimal("200.00"),
        )
        slot = self._make_slot(project)
        amount, _ = calculate_da(slot)
        self.assertEqual(amount, Decimal("0.0"))

class ProjectMaterialTests(TestCase):
    def setUp(self):
        self.url = reverse('project:project-dashboard')
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin2', password='pass1234', is_staff=True
        )
        self.project_type = ProjectType.objects.create(name='Turnkey')
        self.status = ProjectStatus.objects.create(name='Active')
        self.location = LocationType.objects.create(name='Other')

    def test_materials_saved_for_turnkey_project(self):
        self.client.login(username='admin2', password='pass1234')
        data = {
            'add_project': '1',
            'name': 'Proj',
            'customer_name': 'Cust',
            'start_date': '2025-01-01',
            'status_type': self.status.id,
            'project_type': self.project_type.id,
            'location_type': self.location.id,
            'budget': '1000',
            'selected_skills': '[]',
            'projectmaterial_set-TOTAL_FORMS': '1',
            'projectmaterial_set-INITIAL_FORMS': '0',
            'projectmaterial_set-MIN_NUM_FORMS': '0',
            'projectmaterial_set-MAX_NUM_FORMS': '1000',
            'projectmaterial_set-0-id': '',
            'projectmaterial_set-0-name': 'Cement',
            'projectmaterial_set-0-make': 'BrandX',
            'projectmaterial_set-0-quantity': '5',
            'projectmaterial_set-0-price': '20.00',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(name='Proj')
        material = project.materials.get()
        self.assertEqual(material.name, 'Cement')

    def test_turnkey_requires_materials(self):
        self.client.login(username='admin2', password='pass1234')
        data = {
            'add_project': '1',
            'name': 'Proj2',
            'customer_name': 'Cust',
            'start_date': '2025-01-01',
            'status_type': self.status.id,
            'project_type': self.project_type.id,
            'location_type': self.location.id,
            'budget': '1000',
            'selected_skills': '[]',
            'projectmaterial_set-TOTAL_FORMS': '1',
            'projectmaterial_set-INITIAL_FORMS': '0',
            'projectmaterial_set-MIN_NUM_FORMS': '0',
            'projectmaterial_set-MAX_NUM_FORMS': '1000',
            'projectmaterial_set-0-id': '',
            'projectmaterial_set-0-name': '',
            'projectmaterial_set-0-make': '',
            'projectmaterial_set-0-quantity': '',
            'projectmaterial_set-0-price': '',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Project.objects.filter(name='Proj2').count(), 0)        