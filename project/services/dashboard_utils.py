# project/services/dashboard_utils.py

from collections import defaultdict

def transform_timesheets_for_dashboard(timesheets_queryset):
    """
    Groups timesheets by employee and marks if any timesheet is pending.
    Returns:
    - grouped_timesheets: { employee_obj: [Timesheet, ...] }
    - pending_flags: { employee_id: True/False }
    """
    grouped_timesheets = defaultdict(list)
    pending_flags = {}

    for ts in timesheets_queryset:
        grouped_timesheets[ts.employee].append(ts)
        if ts.status == 'Pending':
            pending_flags[ts.employee.id] = True

        # Set DA display string for template rendering
        if ts.daily_allowance_amount and ts.daily_allowance_currency:
            ts.da_display = f"{ts.daily_allowance_currency} {ts.daily_allowance_amount}"
        else:
            ts.da_display = None

    return dict(grouped_timesheets), pending_flags
