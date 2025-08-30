from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from collections import defaultdict
from django.db.models import Sum
from expenses.models import AdvanceAdjustmentLog

from utils.currency import format_currency
import io
import xlsxwriter
from django.http import HttpResponse
from django.utils.timezone import localtime
from expenses.models import AdvanceRequest
from expenses.models import Expense, DailyAllowance

@login_required
@permission_required('expenses.can_approve')
def expense_approval_dashboard(request):
    selected_project = request.GET.get('project')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    expenses = Expense.objects.select_related('project', 'employee').filter(
        status__in=["Pending", "Submitted", "Forwarded to Manager", "Approved", "Rejected"]
    )
    pending_das = DailyAllowance.objects.select_related('project', 'employee').filter(
        approved=False, rejected=False
    )
    advance_requests = AdvanceRequest.objects.select_related('employee', 'project').filter(
        approved_by_manager=True,
        approved_by_accountant=False
    )

    if selected_project and selected_project != "all":
        expenses = expenses.filter(project_id=selected_project)
        pending_das = pending_das.filter(project_id=selected_project)
        advance_requests = advance_requests.filter(project_id=selected_project)

    if from_date:
        expenses = expenses.filter(date__gte=from_date)
        pending_das = pending_das.filter(date__gte=from_date)
        advance_requests = advance_requests.filter(date_requested__gte=from_date)

    if to_date:
        expenses = expenses.filter(date__lte=to_date)
        pending_das = pending_das.filter(date__lte=to_date)
        advance_requests = advance_requests.filter(date_requested__lte=to_date)

    tabbed_expenses = {
        'submitted': [],
        'approved': [],
        'reimbursement': [],
        'settled': [],
        'advance': []
    }

    for expense in expenses:
        entry = {
            "type": "Expense",
            "employee": expense.employee,
            "project": expense.project,
            "amount": format_currency(expense.amount, getattr(expense, 'currency', 'INR')),
            "date": expense.date,
            "status": expense.status,
            "reimbursed": expense.reimbursed,
            "new_expense_type": expense.new_expense_type,
            "id": expense.id,
            "advance_used": expense.advance_used.id if expense.advance_used else None,
            "from_location": expense.from_location,
            "to_location": expense.to_location,
            "receipt": expense.receipt.url if expense.receipt else None,
        }

        if expense.status == "Submitted":
            tabbed_expenses["submitted"].append(entry)
        elif expense.status == "Forwarded to Manager":
            # Do NOT show in accountant’s action tabs
            continue
        elif expense.status == "Approved" and not expense.reimbursed:
            tabbed_expenses["reimbursement"].append(entry)
        elif expense.status == "Approved" and expense.reimbursed:
            tabbed_expenses["settled"].append(entry)
        else:
            tabbed_expenses["approved"].append(entry)


    

    for adv in advance_requests:
        entry = {
            "type": "Advance",
            "employee": adv.employee,
            "project": adv.project,
            "amount": format_currency(adv.amount, 'INR'),
            "date": adv.date_requested,
            "status": "Pending",
            "reimbursed": False,
            "id": adv.id,
            "purpose": adv.purpose,
            "approved_by_manager": adv.approved_by_manager,
            "approved_by_accountant": adv.approved_by_accountant,
        }
        tabbed_expenses["advance"].append(entry)

    projects = Expense.objects.values('project__id', 'project__name').distinct()

    return render(request, 'expenses/expense_approval_dashboard.html', {
        'tabbed_expenses': tabbed_expenses,
        'tab_names': ["submitted", "approved", "reimbursement", "settled", "advance"],
        'projects': projects,
        'pending_das': pending_das,
    })


@login_required
@permission_required('expenses.can_approve')
@require_POST
def approve_or_reject_expense(request, expense_id, action):
    expense = get_object_or_404(Expense, id=expense_id)
    expenses = Expense.objects.select_related('project', 'employee').filter(
        status__in=["Submitted", "Forwarded to Manager", "Forwarded to Account Manager", "Approved", "Rejected"]
    )

    if action == "approve":
        expense.status = "Forwarded to Manager"
        expense.forwarded_to_manager = True
        expense.forwarded_to_accountmanager = False
        expense.save()
        messages.success(request, f"Expense {expense.id} forwarded to Manager.")

        if expense.advance_used is None:
            latest_advance = (
                AdvanceRequest.objects.filter(
                    employee=expense.employee,
                    settled_by_account_manager=True
                )
                .order_by('-settlement_date')
                .first()
            )

            if latest_advance:
                used_sum = latest_advance.used_expenses.aggregate(Sum("amount"))['amount__sum'] or 0
                remaining_balance = latest_advance.amount - used_sum

                deduct_amount = min(expense.amount, remaining_balance)
                expense.advance_used = latest_advance
                expense.save()

                AdvanceAdjustmentLog.objects.create(
                    expense=expense,
                    advance=latest_advance,
                    amount_deducted=deduct_amount
                )

                if expense.amount > remaining_balance:
                    messages.success(
                        request,
                        f"Expense ID {expense.id} approved and linked to Advance ID {latest_advance.id}. Only ₹{deduct_amount} could be deducted due to insufficient balance."
                    )
                else:
                    messages.success(
                        request,
                        f"Expense ID {expense.id} approved and fully deducted ₹{expense.amount} from Advance ID {latest_advance.id}."
                    )
            else:
                expense.save()
                messages.success(request, f"Expense ID {expense.id} approved with no advance available for deduction.")
        else:
            expense.save()
            messages.success(request, f"Expense ID {expense.id} approved and already linked to Advance ID {expense.advance_used.id}.")

    elif action == "reject":
        expense.status = "Rejected"
        expense.forwarded_to_manager = False
        expense.forwarded_to_accountmanager = False
        expense.save()
        messages.warning(request, f"Expense ID {expense.id} has been rejected.")

    else:
        messages.error(request, "Invalid action.")

    return redirect('expenses:expense-approval-dashboard')


@login_required
@permission_required('expenses.can_approve')
def approve_daily_allowance(request, da_id):
    da = get_object_or_404(DailyAllowance, id=da_id)

    if da.approved:
        messages.info(request, "DA is already approved.")
    else:
        if hasattr(da, "mark_approved"):
            da.mark_approved(user=request.user)
        else:
            da.approved = True
            if hasattr(da, "rejected"):
                da.rejected = False
            da.save(update_fields=["approved"] + (["rejected"] if hasattr(da, "rejected") else []))
        messages.success(request, f"DA for {da.employee.user.get_full_name()} on {da.date} approved.")
    return redirect('expenses:expense-approval-dashboard')


@login_required
@user_passes_test(is_accountant)
@require_POST
def reject_daily_allowance(request, da_id):
    da = get_object_or_404(DailyAllowance, id=da_id)

    if getattr(da, "rejected", False):
        messages.info(request, "DA is already rejected.")
    else:
        
        if hasattr(da, "mark_rejected"):
            da.mark_rejected(user=request.user)
        else:
            da.approved = False
            if hasattr(da, "rejected"):
                da.rejected = True
            da.save(update_fields=["approved"] + (["rejected"] if hasattr(da, "rejected") else []))
        messages.warning(request, f"DA for {da.employee.user.get_full_name()} on {da.date} rejected.")

    return redirect('accountant:expense-approval-dashboard')


@login_required
@permission_required('expenses.can_approve')
def export_expense_tab_excel(request, tab_name):
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    selected_project = request.GET.get('project')

    expenses = Expense.objects.select_related('project', 'employee', 'new_expense_type').all()
    allowances = DailyAllowance.objects.select_related('project', 'employee').all()

    if selected_project and selected_project != "all":
        expenses = expenses.filter(project_id=selected_project)
        allowances = allowances.filter(project_id=selected_project)
    if from_date:
        expenses = expenses.filter(date__gte=from_date)
        allowances = allowances.filter(date__gte=from_date)
    if to_date:
        expenses = expenses.filter(date__lte=to_date)
        allowances = allowances.filter(date__lte=to_date)

    rows = []

    for expense in expenses:
        status = expense.status
        reimbursed = expense.reimbursed
        match = (
            (tab_name == "pending" and status == "Pending") or
            (tab_name == "approved" and status == "Approved" and not reimbursed) or
            (tab_name == "reimbursement" and status == "Approved" and not reimbursed) or
            (tab_name == "settled" and status == "Approved" and reimbursed)
        )
        if match:
            rows.append({
                "employee": expense.employee.user.get_full_name(),
                "project": expense.project.name,
                "amount": float(expense.amount),
                "type": expense.new_expense_type.name,
                "date": expense.date.strftime("%Y-%m-%d"),
                "status": status,
                "reimbursed": "Yes" if reimbursed else "No",
                "from_location": expense.from_location or "",
                "to_location": expense.to_location or ""
            })

    for da in allowances:
        status = "Approved" if da.approved else "Pending"
        reimbursed = da.reimbursed
        match = (
            (tab_name == "pending" and not da.approved) or
            (tab_name == "reimbursement" and da.approved and not reimbursed) or
            (tab_name == "settled" and da.approved and reimbursed)
        )
        if match:
            rows.append({
                "employee": da.employee.user.get_full_name(),
                "project": da.project.name,
                "amount": float(da.da_amount),
                "type": "Daily Allowance",
                "date": da.date.strftime("%Y-%m-%d"),
                "status": status,
                "reimbursed": "Yes" if reimbursed else "No",
                "from_location": "",
                "to_location": ""
            })

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet(tab_name.capitalize())

    headers = ["Employee", "Project", "Amount", "Type", "Date", "Status", "Reimbursed", "From Location", "To Location"]
    for col, header in enumerate(headers):
        sheet.write(0, col, header)

    for row_idx, row in enumerate(rows, start=1):
        for col_idx, key in enumerate(headers):
            key_clean = key.lower().replace(" ", "_")
            sheet.write(row_idx, col_idx, row.get(key_clean, ""))

    workbook.close()
    output.seek(0)

    filename = f"{tab_name}_export_{localtime().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response

