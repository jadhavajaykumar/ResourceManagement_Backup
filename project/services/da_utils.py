from expenses.models import DailyAllowance
from project.services.da_service import calculate_da
from timesheet.models import TimeSlot
from collections import defaultdict
from decimal import Decimal

def generate_da_for_timesheet(timesheet):
    """
    Generate and store Daily Allowance entries for a given approved timesheet.
    One DA entry per unique (employee, project, date) combination.
    """
    slots = timesheet.time_slots.select_related('project').all()
    grouped = defaultdict(list)

    for slot in slots:
        key = (slot.project.id, slot.slot_date)
        grouped[key].append(slot)

    for (project_id, slot_date), slot_group in grouped.items():
        any_slot = slot_group[0]
        if not any_slot or not any_slot.project:
            print(f"❌ Missing project info in timeslot for timesheet ID {timesheet.id} on {slot_date}")
            continue

        employee = timesheet.employee
        project = any_slot.project
        total_hours = sum(slot.hours for slot in slot_group)

        try:
            da_amount, currency = calculate_da(any_slot)

            if da_amount and da_amount > 0:
                existing = DailyAllowance.objects.filter(
                    timesheet=timesheet,
                    employee=employee,
                    project=project,
                    date=slot_date
                ).first()

                if not existing:
                    DailyAllowance.objects.create(
                        timesheet=timesheet,
                        employee=employee,
                        project=project,
                        date=slot_date,
                        da_amount=Decimal(str(da_amount)),
                        currency=currency,
                        is_extended=(total_hours > 10),
                        approved=True
                    )
        except Exception as e:
            print(f"DA calculation error for project={project}, date={slot_date}: {e}")
            continue
