# project/services/da_service.py
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Tuple, Optional
from django.db.models import Prefetch
from timesheet.models import Timesheet

from project.models import DASetting  # if you use it elsewhere; kept as-is
from timesheet.models import TimeSlot
from expenses.models import GlobalDASettings, CountryDASetting, DailyAllowance  # ← add DailyAllowance


# --- BRIDGE WEEKEND LOGIC: Fri <-> Mon inference ---



def _eligible_projects_from_timesheet(ts):
    """Return a set of eligible (Domestic/International) projects used in the timesheet."""
    if not ts:
        return set()
    slots = ts.time_slots.select_related('project', 'project__location_type')
    elig = set()
    for s in slots:
        p = s.project
        if not p:
            continue
        loc = getattr(getattr(p, 'location_type', None), 'name', '')
        if str(loc).upper() in {'DOMESTIC', 'INTERNATIONAL'}:
            elig.add(p)
    return elig

def ensure_weekend_from_bridge(timesheet):
    """
    If 'timesheet' is Monday, and there exists a Friday timesheet for the same employee,
    and BOTH days contain at least one Domestic/International project, then:
      - Create DA for Saturday and Sunday (weekend) even with no timesheet.
      - If Friday and Monday projects differ, attribute Saturday to Friday-project, Sunday to Monday-project.
      - If only one side has eligible projects, attribute both weekend days to that side’s project.
    Created DA is unapproved so managers can approve/reject as needed.
    """
    d = timesheet.date if hasattr(timesheet, 'date') else None
    # If your Timesheet model uses a field like 'for_date' or 'slot_date', adjust the attribute above.
    if not d:
        # Fallback: infer from a slot
        slot = timesheet.time_slots.first()
        if not slot:
            return
        d = slot.slot_date

    # Only trigger when we are on a MONDAY
    if d.weekday() != 0:
        return

    emp = timesheet.employee

    # previous Friday
    fri = d - timedelta(days=3)
    sat = d - timedelta(days=2)  # between Fri and Mon
    sun = d - timedelta(days=1)

    ts_fri = Timesheet.objects.filter(employee=emp, date=fri).first()
    # If your model uses different field name, change .filter(employee=..., date=fri)

    # Collect eligible projects on both sides
    fri_projects = _eligible_projects_from_timesheet(ts_fri)
    mon_projects = _eligible_projects_from_timesheet(timesheet)

    if not fri_projects and not mon_projects:
        return  # No eligible projects on either side -> no entitlement

    # Choose project(s) for Sat/Sun
    # Policy:
    #  - If both sides have eligible projects and they differ:
    #       Sat -> a Friday project (arbitrary pick if multiple)
    #       Sun -> a Monday project
    #  - If only one side has eligible projects:
    #       Both days -> that side's project (first eligible)
    sat_project = None
    sun_project = None

    if fri_projects and mon_projects:
        sat_project = next(iter(fri_projects))
        sun_project = next(iter(mon_projects))
    elif fri_projects:
        p = next(iter(fri_projects))
        sat_project = p
        sun_project = p
    else:  # mon_projects only
        p = next(iter(mon_projects))
        sat_project = p
        sun_project = p

    # Create/ensure the weekend DA (idempotent)
    if sat_project:
        ensure_weekend_da(emp, sat_project, sat)
    if sun_project:
        ensure_weekend_da(emp, sun_project, sun)


# ---------------------- Existing helpers (kept) ----------------------
def _week_bounds(d):
    # Monday=0 ... Sunday=6  → return (monday, sunday)
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday
    
def ensure_weekend_for_timesheet(timesheet):
    """
    After a timesheet is submitted/approved, ensure Sat/Sun DA exists
    for each project used in that timesheet's week, even if no timesheet
    was submitted for Sat/Sun.
    """
    slots = timesheet.time_slots.select_related('project').all()
    if not slots:
        return

    employee = timesheet.employee
    # Get the whole week window covering this timesheet's min..max date
    dates = [s.slot_date for s in slots]
    d_min, d_max = min(dates), max(dates)
    week_start, week_end = _week_bounds(d_min)
    # If the min and max are in different weeks, also cover the max week
    ws2, we2 = _week_bounds(d_max)
    week_windows = {(week_start, week_end), (ws2, we2)}

    projects = {s.project for s in slots if s.project}

    for (ws, we) in week_windows:
        # Check Sat/Sun only
        sat = ws + timedelta(days=5)
        sun = ws + timedelta(days=6)
        for p in projects:
            ensure_weekend_da(employee, p, sat)
            ensure_weekend_da(employee, p, sun)

def calculate_total_hours(time_from, time_to) -> float:
    """Calculate total hours between two time values."""
    delta = datetime.combine(datetime.today(), time_to) - datetime.combine(datetime.today(), time_from)
    return delta.total_seconds() / 3600

def get_total_local_hours_on_date(employee, date_):
    """Sum total hours worked by employee on local projects for a given date."""
    slots = TimeSlot.objects.filter(
        employee=employee,
        slot_date=date_,
        project__location_type__name__iexact='Local'
    )
    return sum(slot.hours for slot in slots)

def get_domestic_days_worked(employee, project):
    """Count number of distinct days employee worked on a domestic project."""
    slots = TimeSlot.objects.filter(
        employee=employee,
        project=project,
        project__location_type__name__iexact='Domestic'
    ).values('slot_date').distinct()
    return slots.count()

# ---------------------- Timesheet-based DA (kept, with tiny fix) ----------------------

def calculate_da(slot) -> Tuple[Decimal, str]:
    """
    Calculate Daily Allowance based on project type and configuration.
    Works for Local, Domestic, and International projects.
    """
    timesheet = getattr(slot, 'timesheet', None)
    if not timesheet:
        raise ValueError("Timeslot is not linked to a timesheet")

    project = slot.project
    location_type = project.location_type.name if getattr(project, 'location_type', None) else None
    da_type = getattr(project, 'da_type', None)
    da_rate = getattr(project, 'da_rate_per_unit', None) or Decimal("0.0")
    weekday = slot.slot_date.weekday()

    total_hours = sum(s.hours for s in slot.timesheet.time_slots.filter(project=project))

    # Default currency fallback
    currency = getattr(project, 'currency', None) or "INR"

    if location_type == "Local":
        # Local project DA: flat rate per day (your current rule)
        return Decimal("300.00"), currency

    elif location_type == "Domestic":
        # Domestic project DA: ₹600 per day (your current rule)
        return Decimal("600.00"), currency

    elif location_type == "International":
        # Weekend / off-day DA (Sat/Sun) - when actually worked on weekend
        if weekday in [5, 6] and total_hours > 0:
            return (getattr(project, 'off_day_da_rate', None) or Decimal("0.0")), currency

        if da_type == "Hourly":
            return da_rate * Decimal(str(total_hours)), currency
        elif da_type == "Daily":
            return da_rate, currency

    # Fallback (config incomplete)
    return Decimal("0.0"), currency

# ---------------------- ADDED: Weekend entitlement path ----------------------

WEEKEND_DAYS = (5, 6)  # Saturday=5, Sunday=6

def _is_weekend(d: date) -> bool:
    return d.weekday() in WEEKEND_DAYS

def _eligible_for_weekend_da(project) -> bool:
    """Weekend entitlement applies only to Domestic / International."""
    loc = getattr(getattr(project, 'location_type', None), 'name', '')
    return str(loc).upper() in {"DOMESTIC", "INTERNATIONAL"}

def _weekend_entitlement_amount(project) -> Tuple[Decimal, str]:
    """
    Decide the weekend entitlement amount for a project WITHOUT any timesheet.
    Rules (aligned to your current policy):
      - Domestic: ₹600/day (flat)
      - International: Prefer project.off_day_da_rate if present; else:
                       if project.da_type == Daily → use da_rate_per_unit;
                       otherwise fallback to GlobalDASettings.international_da
    """
    currency = getattr(project, 'currency', None) or "INR"
    loc = getattr(getattr(project, 'location_type', None), 'name', '')

    if str(loc) == "Domestic":
        return Decimal("600.00"), currency

    if str(loc) == "International":
        off_day = getattr(project, 'off_day_da_rate', None)
        if off_day:
            return off_day, currency

        da_type = getattr(project, 'da_type', None)
        if da_type == "Daily":
            return (getattr(project, 'da_rate_per_unit', None) or Decimal("0.0")), currency

        # fallback to global international DA if configured
        try:
            g = GlobalDASettings.objects.first()
            if g and g.international_da:
                return Decimal(str(g.international_da)), currency
        except Exception:
            pass
        return Decimal("0.0"), currency

    return Decimal("0.0"), currency

def ensure_weekend_da(employee, project, d: date) -> Optional[DailyAllowance]:
    """
    Ensure a DA record exists for a weekend date on Domestic/International projects,
    even when the employee has NO timesheet for that date.
    - If an entitlement already exists, return it.
    - If a timesheet DA exists, leave it as-is.
    - If later a weekend timesheet is added, you can upgrade the record to TIMESHEET elsewhere.
    """
    if not _is_weekend(d):
        return None
    if not _eligible_for_weekend_da(project):
        return None

    # If a DA already exists (created earlier by entitlement or timesheet), reuse it
    da = DailyAllowance.objects.filter(employee=employee, project=project, date=d).first()
    if da:
        return da

    amount, currency = _weekend_entitlement_amount(project)
    if amount <= 0:
        return None

    da = DailyAllowance.objects.create(
        employee=employee,
        project=project,
        date=d,
        da_amount=amount,
        currency=currency,
        is_weekend=True,
        rejected=False,
        auto_generated=True,
        source='WEEKEND',
        approved=False,                     # stays in your approval flow
        forwarded_to_accountant=False,
        forwarded_to_accountmanager=False,
        reimbursed=False,
        timesheet=None                      # important: entitlement without timesheet
    )
    return da

def backfill_weekend_da_for_range(employee, project, start_date: date, end_date: date):
    """
    Optional batch utility: safe to run multiple times (idempotent by unique_together).
    """
    created = []
    cur = start_date
    while cur <= end_date:
        if _is_weekend(cur) and _eligible_for_weekend_da(project):
            da = ensure_weekend_da(employee, project, cur)
            if da:
                created.append(da)
        cur += timedelta(days=1)
    return created
