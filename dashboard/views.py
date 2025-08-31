# dashboard/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse, NoReverseMatch

def _url(name, *args, **kwargs):
    """Return reverse(name) or None if URL isn't registered."""
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return None

@login_required
def home(request):
    u = request.user
    ep = getattr(u, "employeeprofile", None)
    role = getattr(ep, "role", None) or getattr(u, "role", None) or "Employee"

    # Capabilities (adjust to your perms)
    can_ts_approve  = u.has_perm("timesheet.can_approve")
    can_exp_approve = u.has_perm("expenses.can_approve") or u.has_perm("expenses.can_settle")
    is_am           = u.groups.filter(name__in=["Account Manager", "Account_Manager"]).exists() or role in ["Account Manager", "Account_Manager"]
    is_manager      = u.groups.filter(name="Manager").exists() or role == "Manager"
    is_hr           = u.groups.filter(name="HR").exists() or role == "HR"
    is_director     = u.groups.filter(name="Director").exists() or role == "Director"
    is_staff        = u.is_staff

    def item(title, icon, urlname_list):
        # Try several url names; first that resolves wins
        url = None
        for nm in urlname_list:
            url = _url(nm)
            if url:
                break
        return {
            "title": title,
            "icon": icon,          # Bootstrap icon class without the leading dot
            "url": url or "#",     # Keep a placeholder so card still appears
            "enabled": bool(url),  # If false, card renders disabled state
        }

    # Common for all users
    common = [
        item("My Profile",    "bi-person-circle",       ["employee:employee-profile-home"]),
        item("My Projects",   "bi-kanban",              ["employee:my-projects"]),
        item("My Timesheet",  "bi-calendar-check",      ["timesheet:my-timesheets"]),
        item("Expenses & DA", "bi-cash-coin",           ["expenses:unified-expense-dashboard"]),
        item("Documents",     "bi-file-earmark",        ["docgen:list-templates"]),
        item("Skills",        "bi-stars",               ["skills:skills-home"]),
    ]

    # Manager / Approver features
    manager = []
    if is_manager or can_ts_approve:
        manager.append(item("Timesheet Approvals", "bi-clipboard-check",
                            [
                                "timesheet:timesheet-approval",
                                "timesheet:timesheet-approvals",
                                "timesheet:filtered-timesheet-approvals",
                            ]))
    if is_manager or can_exp_approve:
        manager.append(item("Expense Approvals", "bi-cash-stack",
                            ["expenses:expense-approval-dashboard"]))
                            
    if is_manager or is_director or is_staff:
        manager.append(item("Add New Projects/Tasks", "bi-kanban",
                            ["project:project-dashboard"]))                        

    # Account Manager
    am = []
    if is_am or is_staff:
        am.append(item("Settlement Summary", "bi-journal-check",
                       ["expenses:am-unsettled-summary"]))

    # HR
    hr = []
    if is_hr or is_staff:
        hr.append(item("People Directory", "bi-people", ["employee:employee-list"]))
        hr.append(item("Add Employee", "bi-person-plus", ["employee:add-employee"]))
        

    # Admin/Director
    admin = []
    if is_director or is_staff:
        admin.append(item("Admin", "bi-speedometer2", ["admin:index"]))

    # Build sections for template
    sections = [
        {"label": "My Workspace", "items": common},
    ]
    if manager:
        sections.append({"label": "Manager", "items": manager})
    if am:
        sections.append({"label": "Account Manager", "items": am})
    if hr:
        sections.append({"label": "HR", "items": hr})
    if admin:
        sections.append({"label": "Admin", "items": admin})

    return render(request, "dashboard/home.html", {
        "role": role,
        "sections": sections,
    })
