# project/services/da_utils.py

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
import logging


from timesheet.models import TimeSlot, Timesheet  # kept even if unused elsewhere
from project.services.da_service import (
    calculate_da,
    ensure_weekend_for_timesheet,     # ensure Sat/Sun in same week
    ensure_weekend_from_bridge,       # Fri<->Mon bridge inference
)
from expenses.models import DailyAllowance

logger = logging.getLogger("project.da_utils")

def generate_da_for_timesheet(timesheet):
    """
    Generate and store Daily Allowance entries for a given approved timesheet.
    One DA entry per unique (employee, project, date) combination.

    - If a weekend entitlement DA exists (auto_generated=True), reuse and upgrade it.
    - Otherwise, create a new DA for this timesheet.
    - After processing, also ensure weekend entitlements via:
        * ensure_weekend_for_timesheet(timesheet)
        * ensure_weekend_from_bridge(timesheet)
    """
    slots = timesheet.time_slots.select_related('project').all()
    grouped = defaultdict(list)

    for slot in slots:
        key = (slot.project.id if slot.project else None, slot.slot_date)
        grouped[key].append(slot)

    for (project_id, slot_date), slot_group in grouped.items():
        any_slot = slot_group[0]
        if not any_slot or not any_slot.project:
            print(f"❌ Missing project info in timeslot for timesheet ID {timesheet.id} on {slot_date}")
            continue

        employee = timesheet.employee
        project = any_slot.project
        total_hours = sum(slot.hours for slot in slot_group)

        # -- Calculate DA for this (employee, project, date)
        try:
            da_amount, currency = calculate_da(any_slot)
        except Exception as e:
            print(f"DA calculation error for project={project}, date={slot_date}: {e}")
            continue

        # Skip if zero/non-positive DA
        if not da_amount or da_amount <= 0:
            continue

        # -- Create or upgrade an existing DA (e.g., from weekend entitlement)
        try:
            da, created = DailyAllowance.objects.get_or_create(
                employee=employee,
                project=project,
                date=slot_date,
                defaults={
                    "da_amount": Decimal(str(da_amount)),
                    "currency": currency,
                    "is_extended": (total_hours > 10),
                    "is_weekend": (slot_date.weekday() in (5, 6)),
                    "auto_generated": False,
                    "source": "TIMESHEET",
                    "approved": False,  # require explicit approval for timesheet-derived DA
                    "reimbursed": False,
                    "forwarded_to_accountant": False,
                    "forwarded_to_accountmanager": False,
                    "timesheet": timesheet,
                }
            )
        except Exception as e:
            print(f"DA get_or_create error for project={project}, date={slot_date}: {e}")
            continue

        if not created:
            # Existing record (likely weekend entitlement): upgrade/attach timesheet
            update_fields = []

            if da.timesheet_id != timesheet.id:
                da.timesheet = timesheet
                update_fields.append("timesheet")

            # If entitlement was auto-generated, flip to timesheet source
            if da.auto_generated or da.source != "TIMESHEET":
                da.auto_generated = False
                da.source = "TIMESHEET"
                update_fields += ["auto_generated", "source"]

            # Align amount/currency/is_extended with timesheet calculation
            if da.da_amount != da_amount:
                da.da_amount = Decimal(str(da_amount))
                update_fields.append("da_amount")
            if da.currency != currency:
                da.currency = currency
                update_fields.append("currency")

            new_is_extended = (total_hours > 10)
            if da.is_extended != new_is_extended:
                da.is_extended = new_is_extended
                update_fields.append("is_extended")

            
            if update_fields:
                try:
                    da.save(update_fields=update_fields)
                except Exception as e:
                    print(f"DA update error for project={project}, date={slot_date}: {e}")

    # -- After processing all submitted days, ensure weekend entitlements

   # try:
        #ensure_weekend_for_timesheet(timesheet)
   # except Exception as e:
       # print(f"Weekend DA ensure failed for TS#{timesheet.id}: {e}")

    try:
        ensure_weekend_from_bridge(timesheet)
    except Exception as e:
        print(f"Bridge weekend DA ensure failed for TS#{timesheet.id}: {e}")


def create_weekend_da_entries(timesheet):
    """Create DA entries for Saturday and Sunday preceding a Monday timesheet.

    If the employee worked on the same project on the previous Friday and the
    project is Domestic/International, insert DA rows for Saturday and Sunday.
    Domestic projects get ₹600/day; International use ``off_day_da_rate``.
    Newly created entries are marked ``approved=False`` and ``auto_generated``.
    """
    if not timesheet or timesheet.date.weekday() != 0:  # Only for Mondays
        return

    employee = timesheet.employee
    friday_date = timesheet.date - timedelta(days=3)
    saturday = timesheet.date - timedelta(days=2)
    sunday = timesheet.date - timedelta(days=1)

    friday_ts = (
        Timesheet.objects.filter(employee=employee, date=friday_date, status="Approved")
        .prefetch_related("time_slots__project__location_type")
        .first()
    )
    if not friday_ts:
        return

    mon_projects = {s.project for s in timesheet.time_slots.all() if s.project}
    fri_projects = {s.project for s in friday_ts.time_slots.all() if s.project}

    common_projects = [p for p in mon_projects if p in fri_projects]
    if not common_projects:
        return

    for project in common_projects:
        location = getattr(getattr(project, "location_type", None), "name", "")
        if location == "Domestic":
            amount = Decimal("600")
        elif location == "International":
            amount = project.off_day_da_rate or Decimal("0")
        else:
            continue

        currency = getattr(project, "currency", None) or "INR"

        for d in (saturday, sunday):
            da, created = DailyAllowance.objects.get_or_create(
                employee=employee,
                project=project,
                date=d,
                defaults={
                    "da_amount": Decimal(str(amount)),
                    "currency": currency,
                    "is_extended": False,
                    "is_weekend": True,
                    "auto_generated": True,
                    "source": "WEEKEND",
                    "approved": False,
                    "reimbursed": False,
                    "forwarded_to_accountant": False,
                    "forwarded_to_accountmanager": False,
                    "timesheet": timesheet,
                },
            )

            if not created and da.timesheet_id != timesheet.id:
                da.timesheet = timesheet
                da.save(update_fields=["timesheet"])