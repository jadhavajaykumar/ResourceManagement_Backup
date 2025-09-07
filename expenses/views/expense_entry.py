from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import io
import xlsxwriter
from employee.models import EmployeeProfile
from expenses.models import Expense, DailyAllowance, AdvanceRequest
from expenses.forms import ExpenseForm
from django.template.loader import render_to_string
from project.models import Project
from .unified_expense_dashboard import unified_expense_dashboard
import uuid
import json


# ... other imports above remain ...

def _build_expense_type_meta(field_queryset):
    """
    Build a mapping of expense_type_id -> meta attributes consumed by JS.
    Defensive about attribute names on the model.
    """
    meta = {}
    if not field_queryset:
        return meta

    for et in field_queryset:
        try:
            requires_km = bool(
                getattr(et, "requires_kilometers", None)
                or getattr(et, "requiresKm", None)
                or getattr(et, "requires_km", None)
            )
        except Exception:
            requires_km = False

        # rate field name may vary
        rate = None
        for candidate in ("rate_per_km", "rate", "km_rate", "rate_per_km_inr"):
            rate = getattr(et, candidate, None)
            if rate is not None:
                break
        try:
            rate = float(rate) if rate is not None else 0.0
        except Exception:
            rate = 0.0

        # receipt, travel flags and max cap (optional)
        requires_receipt = bool(getattr(et, "requires_receipt", getattr(et, "requiresReceipt", False)))
        requires_travel = bool(getattr(et, "requires_travel", getattr(et, "requiresTravel", False)))
        max_cap = None
        for cand in ("max_cap", "maxCap", "cap"):
            max_cap = getattr(et, cand, None)
            if max_cap is not None:
                try:
                    max_cap = float(max_cap)
                except Exception:
                    max_cap = None
                break

        meta[str(et.pk)] = {
            "requires_km": requires_km,
            "rate": rate,
            "requires_receipt": requires_receipt,
            "requires_travel": requires_travel,
            "max_cap": max_cap or 0
        }
    return meta


@login_required
def new_expense_form(request):
    prefix = "exp_" + uuid.uuid4().hex[:8]

    form = ExpenseForm(employee=request.user.employeeprofile)
    form.fields['project'].queryset = Project.objects.filter(
        taskassignment__employee=request.user.employeeprofile
    ).distinct()

    # --- Set widget attrs so rendered HTML contains ids/placeholders/etc. ---
    for fname, field in form.fields.items():
        fid = f"{prefix}_{fname}"
        attrs = field.widget.attrs or {}
        # checkbox detection
        base_class = attrs.get("class", "")
        if field.widget.__class__.__name__.lower().find("checkbox") != -1 or getattr(field.widget, "input_type", "") == "checkbox":
            attrs["class"] = (base_class + " form-check-input").strip()
        else:
            attrs["class"] = (base_class + " form-control").strip()

        lab = getattr(field, "label", fname).capitalize()
        attrs.setdefault("id", fid)
        attrs.setdefault("placeholder", lab)
        attrs.setdefault("title", lab)
        attrs.setdefault("aria-label", lab)

        field.widget.attrs = attrs

    # Build expense-type metadata (if the field has a queryset)
    expense_type_field = form.fields.get("new_expense_type")
    meta = {}
    if expense_type_field is not None and getattr(expense_type_field, "queryset", None) is not None:
        meta = _build_expense_type_meta(expense_type_field.queryset)

    form_html = render_to_string(
        "expenses/expense_form_wrapper.html",
        {"form": form, "editing": False, "prefix": prefix},
        request=request
    )

    # Append metadata as an accessible JSON <script> for client-side JS
    meta_script = f'<script type="application/json" id="{prefix}_expense_type_meta">{json.dumps(meta)}</script>'
    form_html_with_meta = form_html + meta_script

    return JsonResponse({"form_html": form_html_with_meta, "prefix": prefix, "editing": False})



@login_required
def edit_expense_json(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id, employee__user=request.user)

    if expense.status != "Submitted":
        return JsonResponse({"error": "Editing is not allowed for approved/rejected expenses."}, status=403)

    employee = request.user.employeeprofile

    form = ExpenseForm(instance=expense, employee=employee)
    form.fields['project'].queryset = Project.objects.filter(
        taskassignment__employee=employee
    ).distinct()

    # Build meta from the expense type field's queryset (same helper)
    expense_type_field = form.fields.get("new_expense_type")
    meta = {}
    if expense_type_field is not None and getattr(expense_type_field, "queryset", None) is not None:
        meta = _build_expense_type_meta(expense_type_field.queryset)

    requires_km = bool(getattr(expense.new_expense_type, "requires_kilometers", False))

    form_html = render_to_string(
        "expenses/expense_form_wrapper.html",
        {
            "form": form,
            "editing": True,
            "expense": expense,
            "requires_km": requires_km,
            "prefix": f"exp_edit_{expense.id}"
        },
        request=request
    )

    # append meta script
    prefix = f"exp_edit_{expense.id}"
    meta_script = f'<script type="application/json" id="{prefix}_expense_type_meta">{json.dumps(meta)}</script>'
    form_html_with_meta = form_html + meta_script

    return JsonResponse({"form_html": form_html_with_meta, "prefix": prefix, "editing": True})

    

@login_required
def get_expense_data(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, employee=request.user.employeeprofile)
    form = ExpenseForm(instance=expense)
    
    form_html = render_to_string("expenses/expense_form_wrapper.html", {
        "form": form,
        "editing": True
    }, request=request)

    return JsonResponse({"success": True, "form_html": form_html})

@login_required
def edit_expense(request, expense_id):
    profile = EmployeeProfile.objects.get(user=request.user)
    expense = get_object_or_404(Expense, id=expense_id, employee=profile)

    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES, instance=expense, employee=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated successfully.")
            return redirect("expenses:unified-expense-dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
            return redirect("expenses:unified-expense-dashboard")
    else:
        form = ExpenseForm(instance=expense, employee=profile)

    return render(request, "expenses/expense_form_wrapper.html", {
        "form": form,
        "editing": True
    })






@login_required
def delete_expense(request, expense_id):
    profile = EmployeeProfile.objects.get(user=request.user)
    expense = get_object_or_404(Expense, id=expense_id, employee=profile)

    # Allow delete only if still at ACCOUNTANT stage and status is Submitted
    if expense.current_stage == "ACCOUNTANT" and expense.status == "Submitted":
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
    else:
        messages.error(
            request,
            "Only submitted expenses at Accountant stage can be deleted."
        )

    return redirect('expenses:unified-expense-dashboard')



@login_required
def export_expense_tab(request, tab_name):
    employee = request.user.employeeprofile

    tabs = {
        "Submitted": Expense.objects.filter(employee=employee, status='Pending'),
        "Approved": Expense.objects.filter(employee=employee, status='Approved', reimbursed=False),
        "Settled": Expense.objects.filter(employee=employee, status='Approved', reimbursed=True),
        "Rejected": Expense.objects.filter(employee=employee, status='Rejected'),
        "Daily Allowance": DailyAllowance.objects.filter(employee=employee),
        "Advance Requests": AdvanceRequest.objects.filter(employee=employee),
    }

    data = tabs.get(tab_name)
    if not data:
        return HttpResponse("Invalid tab name", status=400)

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    sheet = workbook.add_worksheet(tab_name)

    if tab_name in ["Submitted", "Approved", "Settled", "Rejected"]:
        headers = ["Date", "Project", "Type", "Amount", "Status"]
        rows = [
            [str(exp.date), str(exp.project), str(exp.new_expense_type), float(exp.amount), exp.status]
            for exp in data
        ]
    elif tab_name == "Daily Allowance":
        headers = ["Date", "Project", "DA Amount", "Approved"]
        rows = [
            [str(da.date), str(da.project), float(da.da_amount), da.approved]
            for da in data
        ]
    elif tab_name == "Advance Requests":
        headers = ["Date Requested", "Purpose", "Amount", "Settled"]
        rows = [
            [str(adv.date_requested), adv.purpose, float(adv.amount), adv.settled_by_account_manager]
            for adv in data
        ]

    for col, header in enumerate(headers):
        sheet.write(0, col, header)

    for row_idx, row in enumerate(rows, 1):
        for col_idx, cell in enumerate(row):
            sheet.write(row_idx, col_idx, cell)

    workbook.close()
    output.seek(0)

    filename = f"{tab_name}_export.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response
