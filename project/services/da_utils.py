# project/services/da_utils.py

from collections import defaultdict
from decimal import Decimal

from expenses.models import DailyAllowance
from timesheet.models import TimeSlot  # kept even if unused elsewhere
from project.services.da_service import (
    calculate_da,
    ensure_weekend_for_timesheet,     # ensure Sat/Sun in same week
    ensure_weekend_from_bridge,       # Fri<->Mon bridge inference
)


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
                    "approved": True,  # your existing behavior for timesheet-derived DA
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

            # For timesheet-derived DA, ensure approved=True
            if da.approved is False:
                da.approved = True
                update_fields.append("approved")

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
