# expenses/services/da_settlement_service.py

from decimal import Decimal
from django.db.models import Sum
from django.utils.timezone import now
from datetime import date as date_cls

from expenses.models import (
    AdvanceRequest,
    AdvanceAdjustmentLog,
    DailyAllowanceSettlement,
)

def _advance_available_amount(advance: AdvanceRequest) -> Decimal:
    used = AdvanceAdjustmentLog.objects.filter(advance=advance).aggregate(s=Sum("amount_deducted"))["s"] or Decimal("0")
    return Decimal(advance.amount) - Decimal(used)

def _allocate_from_advances(employee, amount: Decimal):
    """
    Greedy allocation against Settled advances (oldest first).
    Returns (allocations, primary, remaining)
    """
    remaining = Decimal(amount)
    allocations = []
    primary = None

    settled = AdvanceRequest.objects.filter(employee=employee, status="Settled").order_by("settlement_date", "id")
    for adv in settled:
        if remaining <= 0:
            break
        free = _advance_available_amount(adv)
        if free <= 0:
            continue
        take = min(free, remaining)
        allocations.append((adv, take))
        if primary is None and take > 0:
            primary = adv
        remaining -= take

    return allocations, primary, remaining

def settle_da(da, prefer_advance: bool, payment_date):
    """
    Returns (ok: bool, message: str)
    - prefer_advance=True: try advances first, otherwise error if none.
    - prefer_advance=False: settle by CASH (requires a payment_date).
    """
    if not da.approved:
        return False, "DA must be approved before settlement."

    if da.reimbursed:
        return False, "This DA is already settled."

    amount = Decimal(da.da_amount)

    # Normalize payment_date
    if not payment_date:
        payment_date = now().date()
    elif isinstance(payment_date, str):
        # view already parses ISO, but be defensive
        try:
            payment_date = date_cls.fromisoformat(payment_date)
        except Exception:
            payment_date = now().date()

    if prefer_advance:
        allocations, primary, remaining = _allocate_from_advances(da.employee, amount)

        if not allocations:
            return False, "No settled advance balance available for this employee."

        deducted_total = Decimal("0")
        for adv, take in allocations:
            AdvanceAdjustmentLog.objects.create(
                da=da,
                advance=adv,
                amount_deducted=take,
            )
            deducted_total += take

        DailyAllowanceSettlement.objects.create(
            da=da,
            method="ADVANCE",
            amount=deducted_total,
            payment_date=payment_date,
            created_by=getattr(da, "_actor", None),  # optional, view can set da._actor = request.user
            note="Auto-adjusted against settled advances",
            primary_advance=primary,
        )

        if deducted_total >= amount:
            da.reimbursed = True
            da.save(update_fields=["reimbursed"])
            return True, f"DA ₹{amount} settled against advances."
        else:
            return True, f"Partially covered ₹{deducted_total}. Remaining ₹{amount - deducted_total} still unsettled."

    # CASH
    DailyAllowanceSettlement.objects.create(
        da=da,
        method="CASH",
        amount=amount,
        payment_date=payment_date,
        created_by=getattr(da, "_actor", None),
        note="Cash/Bank reimbursement",
    )
    da.reimbursed = True
    da.save(update_fields=["reimbursed"])
    return True, f"DA ₹{amount} settled by cash/bank."
