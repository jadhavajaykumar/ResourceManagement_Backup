# expenses/views/unified_expense_dashboard.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.timezone import now
from django.contrib import messages
from expenses.models import Expense, AdvanceRequest, DailyAllowance, AdvanceAdjustmentLog
from employee.models import EmployeeProfile
from expenses.forms import ExpenseForm, AdvanceRequestForm

from django.db.models import Sum, Prefetch


@login_required
def unified_expense_dashboard(request):
    user = request.user
    role = getattr(user.employeeprofile, "role", None)
    employee = getattr(user, "employeeprofile", None)

    # ------------------------------- Forms -------------------------------
    expense_form = ExpenseForm(request.POST or None, request.FILES or None, employee=employee)
    advance_form = AdvanceRequestForm(request.POST or None, employee=employee)

    # ------------------------------- Advance Summary (authoritative) -------------------------------
    # We'll compute the true advance balance from SETTLED advances and AdvanceAdjustmentLog
    employee_for_summary = request.user.employeeprofile

    settled_advances_qs = AdvanceRequest.objects.filter(
        employee=employee_for_summary, status="Settled"
    )

    total_advance_amount = settled_advances_qs.aggregate(s=Sum("amount"))["s"] or 0
    total_deducted = AdvanceAdjustmentLog.objects.filter(
        advance__in=settled_advances_qs
    ).aggregate(s=Sum("amount_deducted"))["s"] or 0

    advance_balance = float(total_advance_amount or 0) - float(total_deducted or 0)

    # Submitted/flowing (not approved/rejected/settled) just for the summary card
    submitted_total = Expense.objects.filter(
        employee=employee_for_summary
    ).exclude(status__in=["Approved", "Rejected", "Settled"]).aggregate(s=Sum("amount"))["s"] or 0

    context_extra = {
        "advance_summary": {
            "total_advance_amount": total_advance_amount,
            "total_deducted": total_deducted,
            "advance_balance": advance_balance,
            "submitted_total": submitted_total,
        }
    }

    # ------------------------------- Latest advance (for modal messaging only) -------------------------------
    # Keep this for info/locking copy in the modal; do NOT use to compute balance
    latest_advance = AdvanceRequest.objects.filter(
        employee=employee
    ).exclude(status="Settled").order_by('-date_requested', '-id').first()

    # Use authoritative balance to decide if a new advance can be raised
    current_balance = advance_balance
    allow_new_advance = current_balance <= 0

    # Side list/history (kept)
    advance_entries = AdvanceRequest.objects.filter(employee=employee).order_by('-date_requested')

    # ------------------------------- Base QS & Prefetch -------------------------------
    expense_qs = Expense.objects.select_related(
        "employee__user", "project", "new_expense_type", "advance_used"
    ).prefetch_related(
        Prefetch("advanceadjustmentlog_set", queryset=AdvanceAdjustmentLog.objects.select_related("advance"))
    )

    # ------------------------------- Handle Submissions -------------------------------
    show_expense_modal = False
    show_advance_modal = False

    if request.method == "POST":
        if "submit_expense" in request.POST:
            if expense_form.is_valid():
                expense = expense_form.save(commit=False)
                expense.employee = employee

                # ✅ Set initial current_stage dynamically based on submitter's role
                if role == "Employee":
                    expense.current_stage = "ACCOUNTANT"
                elif role == "Accountant":
                    expense.current_stage = "MANAGER"
                elif role == "Manager":
                    expense.current_stage = "ACCOUNT_MANAGER"
                elif role == "Account Manager":
                    expense.current_stage = "APPROVED"

                expense.save()
                messages.success(request, "✅ Expense submitted successfully.")
                return redirect("expenses:unified-expense-dashboard")
            else:
                show_expense_modal = True
                messages.error(request, "❌ Please correct the errors in the expense form.")

        elif "submit_advance" in request.POST:
            if not allow_new_advance:
                messages.error(
                    request,
                    f"❌ You cannot raise a new advance request until your current balance of ₹{current_balance:.2f} is cleared."
                )
                show_advance_modal = True
            elif advance_form.is_valid():
                advance = advance_form.save(commit=False)
                advance.employee = employee
                advance.save()
                messages.success(request, "✅ Advance request submitted successfully.")
                return redirect("expenses:unified-expense-dashboard")
            else:
                messages.error(request, "❌ Please correct the errors in the advance request form.")
                show_advance_modal = True

    # ------------------------------- Filters -------------------------------
    current_year = now().year
    year_range = range(current_year - 5, current_year + 1)
    month_choices = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]

    selected_year = request.GET.get("year", current_year)
    selected_month = request.GET.get("month", "")
    selected_project = request.GET.get("project", "")
    selected_employee = request.GET.get("employee", "")

    # ------------------------------- Role-based Querysets -------------------------------
    if role == "Employee":
        expenses = expense_qs.filter(employee=employee)
        advances = AdvanceRequest.objects.filter(employee=employee)
        da_entries = DailyAllowance.objects.filter(employee=employee, approved=True)
        projects = expenses.values("project_id", "project__name").distinct()
        employees = None

    elif role == "Manager":
        reportees = EmployeeProfile.objects.filter(reporting_manager=user)
        expenses = expense_qs.filter(employee__in=reportees)
        advances = AdvanceRequest.objects.filter(employee__in=reportees)
        da_entries = DailyAllowance.objects.filter(employee__in=reportees, approved=True)
        projects = expenses.values("project_id", "project__name").distinct()
        employees = reportees

    elif role in ["Accountant", "Account Manager"]:
        expenses = expense_qs.all()
        advances = AdvanceRequest.objects.all()
        da_entries = DailyAllowance.objects.filter(approved=True)
        projects = expenses.values("project_id", "project__name").distinct()
        employees = EmployeeProfile.objects.all()

    else:
        expenses = expense_qs.none()
        advances = AdvanceRequest.objects.none()
        da_entries = DailyAllowance.objects.none()
        projects = []
        employees = None

    # Prefetch adjustment logs on advances (kept)
    advances = advances.prefetch_related(
        Prefetch(
            "advanceadjustmentlog_set",
            queryset=AdvanceAdjustmentLog.objects.select_related("expense")
        )
    )

    # ------------------------------- Apply Filters -------------------------------
    if selected_year:
        da_entries = da_entries.filter(date__year=selected_year)
    if selected_month:
        da_entries = da_entries.filter(date__month=selected_month)
    if selected_project:
        expenses = expenses.filter(project_id=selected_project)
        advances = advances.filter(project_id=selected_project)
        da_entries = da_entries.filter(project_id=selected_project)
    if role in ["Accountant", "Manager", "Account Manager"] and selected_employee:
        expenses = expenses.filter(employee_id=selected_employee)
        advances = advances.filter(employee_id=selected_employee)
        da_entries = da_entries.filter(employee_id=selected_employee)

    # ------------------------------- Approval Rights -------------------------------
    for exp in expenses:
        exp.can_approve = False
        if role == "Accountant" and exp.current_stage == "ACCOUNTANT":
            exp.can_approve = True
        elif role == "Manager" and exp.current_stage == "MANAGER":
            exp.can_approve = True
        elif role == "Account Manager" and exp.current_stage in ["ACCOUNT_MANAGER", "APPROVED"]:
            exp.can_approve = True

    # ------------------------------- Tabs -------------------------------
    tabs = {
        "pending_expenses": expenses.filter(
            status__in=["Submitted", "Forwarded to Manager", "Forwarded to Account Manager"]
        ),
        "approved_expenses": expenses.filter(status="Approved"),
        "rejected_expenses": expenses.filter(status="Rejected"),
        "settled_expenses": expenses.filter(status="Settled"),

        "pending_advances": advances.filter(
            current_stage__in=["MANAGER", "ACCOUNTANT", "ACCOUNT_MANAGER"]
        ),
        # No "Approved" status exists for advances; closest is forwarded to AM
        "approved_advances": advances.filter(status="Forwarded to Account Manager"),
        "rejected_advances": advances.filter(status="Rejected"),
        "settled_advances": advances.filter(status="Settled"),

        "da_entries": da_entries,
    }

    # ------------------------------- Pagination -------------------------------
    settled_combined = list(tabs["settled_expenses"]) + list(tabs["settled_advances"])
    paginator = Paginator(settled_combined, 10)
    page_number = request.GET.get("page")
    settled_page = paginator.get_page(page_number)

    return render(request, "expenses/unified_expense_dashboard.html", {
        "tabs": tabs,
        "settled_page": settled_page,
        "role": role,
        "year_range": year_range,
        "month_choices": month_choices,
        "selected_year": int(selected_year),
        "selected_month": selected_month,
        "selected_project": selected_project,
        "selected_employee": selected_employee,
        "projects": projects,
        "employees": employees,
        "expense_form": expense_form,
        "advance_form": advance_form,
        "latest_advance": latest_advance,
        "current_balance": current_balance,
        "allow_new_advance": allow_new_advance,
        "advance_entries": advance_entries,
        "expense_action": "approve_reject" if role in ["Accountant", "Manager", "Account Manager"] else "resubmit_or_view",
        "show_expense_modal": show_expense_modal,
        "show_advance_modal": show_advance_modal,
        "advance_summary": context_extra["advance_summary"],
    })
