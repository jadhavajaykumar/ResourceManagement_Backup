

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import io
import xlsxwriter
from employee.models import EmployeeProfile
from expenses.models import Expense, DailyAllowance, AdvanceRequest
from expenses.forms import ExpenseForm, AdvanceRequestForm
from django.template.loader import render_to_string
from project.models import Project
from .unified_expense_dashboard import unified_expense_dashboard


@login_required
def employee_expenses(request):
    """Legacy wrapper that delegates to the unified dashboard view."""
    return redirect('expenses:unified-expense-dashboard')

@login_required
def new_expense_form(request):
    employee = request.user.employeeprofile
    form = ExpenseForm(employee=employee)
    form.fields['project'].queryset = Project.objects.filter(
        taskassignment__employee=employee
    ).distinct()

    form_html = render_to_string(
        "expenses/expense_form_wrapper.html",
        {"form": form, "editing": False},
        request=request
    )
    return JsonResponse({"form_html": form_html})


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

    # Determine if kilometers should be shown initially
    requires_km = getattr(expense.new_expense_type, "requires_kilometers", False)

    form_html = render_to_string(
        "expenses/expense_form_wrapper.html",
        {
            "form": form,
            "editing": True,
            "expense": expense,
            "requires_km": requires_km  # Pass to JS/UI
        },
        request=request
    )
    return JsonResponse({"form_html": form_html})
    
@login_required
def delete_advance(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, id=advance_id, employee=request.user.employeeprofile)

    if advance.status == "Submitted" and advance.current_stage == "MANAGER":
        advance.delete()
        messages.success(request, "Advance request deleted successfully.")
    else:
        messages.error(request, "Only submitted advances at Manager stage can be deleted.")

    return redirect('expenses:unified-expense-dashboard')


@login_required
def edit_advance(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, id=advance_id, employee=request.user.employeeprofile)

    if request.method == "POST":
        form = AdvanceRequestForm(request.POST, instance=advance)
        if form.is_valid():
            form.save()
            messages.success(request, "Advance request updated successfully.")
            return redirect('expenses:unified-expense-dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
            return redirect('expenses:unified-expense-dashboard')

    return redirect('expenses:unified-expense-dashboard')


@login_required
def edit_advance_json(request, advance_id):
    advance = get_object_or_404(AdvanceRequest, pk=advance_id, employee__user=request.user)

    # 🔒 Allow edit only if still at MANAGER stage + Submitted
    if not (advance.status == "Submitted" and advance.current_stage == "MANAGER"):
        return JsonResponse({"error": "Editing is allowed only at Manager stage while Submitted."}, status=403)

    form = AdvanceRequestForm(instance=advance, employee=request.user.employeeprofile)
    form_html = render_to_string(
        "expenses/advance_form_partial.html",
        {"form": form, "editing": True, "advance": advance},
        request=request
    )
    return JsonResponse({"form_html": form_html})





    






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
