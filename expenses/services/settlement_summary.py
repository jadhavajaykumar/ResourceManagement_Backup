# expenses/services/settlement_summary.py
# expenses/services/settlement_summary.py
from django.core.exceptions import FieldDoesNotExist
from collections import defaultdict
from decimal import Decimal
from django.db.models import Sum, Q, Prefetch
from expenses.models import Expense, AdvanceRequest, AdvanceAdjustmentLog, DailyAllowance
from django.utils.timezone import now

# ---------- helpers: advance math ----------
def _advance_remaining(advance: AdvanceRequest) -> Decimal:
    """
    Remaining amount on an advance = advance.amount - sum(deductions already logged).
    We keep your existing convention: you consider balances only from advances with status='Settled'.
    """
    total_deducted = (
        AdvanceAdjustmentLog.objects.filter(advance=advance)
        .aggregate(s=Sum("amount_deducted"))["s"] or Decimal("0")
    )
    amt = Decimal(str(getattr(advance, "amount", 0) or 0))
    return amt - Decimal(total_deducted)

def _get_employee_advances(employee):
    """
    Advances from which we are allowed to deduct (same convention used in your dashboard summary):
    status='Settled'. We order most recent first, but you can change if FIFO is preferred.
    """
    return AdvanceRequest.objects.filter(
        employee=employee,
        status="Settled",
    ).order_by("-date_requested", "-id")

def _deduct_from_advances(employee, amount: Decimal, *, source_expense=None, source_da=None):
    """
    Deduct 'amount' from employee's available advances, logging AdvanceAdjustmentLog rows.
    Returns (deducted_total, remaining_after_deduction).
    """
    to_deduct = Decimal(amount)
    deducted = Decimal("0")

    for adv in _get_employee_advances(employee):
        remaining = _advance_remaining(adv)
        if remaining <= 0:
            continue
        slice_amt = min(remaining, to_deduct)
        if slice_amt <= 0:
            break
        log = AdvanceAdjustmentLog.objects.create(
            expense=source_expense,
            da=source_da,
            advance=adv,
            amount_deducted=slice_amt,
        )
        deducted += slice_amt
        to_deduct -= slice_amt
        if to_deduct <= 0:
            break

    return deducted, to_deduct  # to_deduct is the leftover

# ---------- public: summarize unsettled ----------
def build_unsettled_summary():
    """
    Returns a dict keyed by employee profile with:
      {
        'expenses_qs': approved & not settled expenses,
        'da_qs': approved & not reimbursed DAs,
        'total_expenses': Decimal,
        'total_da': Decimal,
        'grand_total': Decimal
      }
    """
    # Expenses: Approved but not settled
    exp_qs = Expense.objects.select_related(
        "employee__user", "project", "new_expense_type", "advance_used"
    ).filter(status="Approved")

    # If your Expense model has any boolean like `reimbursed` / `settled`,
    # add it here to exclude already-settled. Otherwise 'Approved' is the gate.
    # e.g.: .filter(reimbursed=False)  # uncomment if exists

    # DA: Approved but not reimbursed
    da_qs = DailyAllowance.objects.select_related("employee__user", "project").filter(
        approved=True, reimbursed=False
    )

    # Group totals by employee
    per_emp = defaultdict(lambda: {
        "expenses_qs": None,
        "da_qs": None,
        "total_expenses": Decimal("0"),
        "total_da": Decimal("0"),
        "grand_total": Decimal("0"),
    })

    # expenses
    exp_totals = (
        exp_qs.values("employee_id")
        .annotate(total=Sum("amount"))
    )
    totals_by_emp = {row["employee_id"]: row["total"] or Decimal("0") for row in exp_totals}
    for e in exp_qs:
        d = per_emp[e.employee]
        d["expenses_qs"] = (d["expenses_qs"] or exp_qs.filter(employee=e.employee))
        d["total_expenses"] = Decimal(totals_by_emp.get(e.employee_id) or 0)

    # da
    da_totals = (
        da_qs.values("employee_id")
        .annotate(total=Sum("da_amount"))
    )
    da_by_emp = {row["employee_id"]: row["total"] or Decimal("0") for row in da_totals}
    for da in da_qs:
        d = per_emp[da.employee]
        d["da_qs"] = (d["da_qs"] or da_qs.filter(employee=da.employee))
        d["total_da"] = Decimal(da_by_emp.get(da.employee_id) or 0)

    # compute grand total
    for emp, d in per_emp.items():
        d["grand_total"] = (d["total_expenses"] or 0) + (d["total_da"] or 0)

    # Remove employees where both are zero (unlikely)
    return {emp: d for emp, d in per_emp.items() if d["grand_total"] > 0}


# ---------- public: bulk settlement ----------


def _has_db_field(model_instance, field_name: str) -> bool:
    try:
        model_instance._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False

def settle_everything_for_employee(employee, *, payment_date=None):
    payment_date = payment_date or now().date()

    expenses = Expense.objects.filter(employee=employee, status="Approved")
    das = DailyAllowance.objects.filter(employee=employee, approved=True, reimbursed=False)

    results = {
        "expense_count": expenses.count(),
        "da_count": das.count(),
        "deducted_from_advance": Decimal("0"),
        "cash_paid": Decimal("0"),
    }

    # --- Expenses ---
    for exp in expenses:
        amt = Decimal(str(getattr(exp, "amount", 0) or 0))

        deducted, leftover = _deduct_from_advances(employee, amt, source_expense=exp)
        results["deducted_from_advance"] += deducted

        exp.status = "Settled"
        update_fields = ["status"]

        if _has_db_field(exp, "settlement_date"):
            exp.settlement_date = payment_date
            update_fields.append("settlement_date")

        exp.save(update_fields=update_fields)
        results["cash_paid"] += max(leftover, Decimal("0"))

    # --- DAs ---
    for da in das:
        amt = Decimal(str(getattr(da, "da_amount", 0) or 0))

        deducted, leftover = _deduct_from_advances(employee, amt, source_da=da)
        results["deducted_from_advance"] += deducted

        da.reimbursed = True
        update_fields = ["reimbursed"]

        if _has_db_field(da, "settlement_date"):
            da.settlement_date = payment_date
            update_fields.append("settlement_date")

        da.save(update_fields=update_fields)
        results["cash_paid"] += max(leftover, Decimal("0"))

    msg = (
        f"Settled {results['expense_count']} expense(s) and {results['da_count']} DA(s). "
        f"Advance deductions: ₹{results['deducted_from_advance']:.2f}, "
        f"Cash paid: ₹{results['cash_paid']:.2f}."
    )
    return True, msg, results

