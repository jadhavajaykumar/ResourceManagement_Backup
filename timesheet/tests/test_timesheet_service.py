from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from employee.models import EmployeeProfile
from project.models import LocationType, Project
from timesheet.models import (
    CompensatoryOff,
    Holiday,
    Timesheet,
    TimeSlot,
)
from timesheet.services.timesheet_service import process_timesheet_save


class ProcessTimesheetSaveTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="holiday-user", password="pw"
        )
        self.employee = EmployeeProfile.objects.get(user=self.user)
        self.location_type = LocationType.objects.create(name="Office")
        self.project = Project.objects.create(
            name="Holiday Project",
            customer_name="Holiday Customer",
            start_date=date.today(),
            location_type=self.location_type,
        )

    def test_process_timesheet_save_creates_comp_off_for_holiday(self):
        holiday_date = date(2024, 1, 1)
        Holiday.objects.create(date=holiday_date, description="Test Holiday")
        timesheet = Timesheet.objects.create(
            employee=self.employee,
            date=holiday_date,
            shift_start=time(9, 0),
            shift_end=time(17, 0),
        )
        TimeSlot.objects.create(
            timesheet=timesheet,
            project=self.project,
            employee=self.employee,
            date=holiday_date,
            slot_date=holiday_date,
            time_from=time(9, 0),
            time_to=time(17, 0),
            description="Worked on holiday",
            hours=Decimal("8.0"),
        )

        process_timesheet_save(timesheet)

        comp_off = CompensatoryOff.objects.get(timesheet=timesheet)
        self.assertEqual(float(comp_off.credited_days), 1.0)
        self.assertFalse(comp_off.approved)
        self.assertEqual(comp_off.date_earned, holiday_date)