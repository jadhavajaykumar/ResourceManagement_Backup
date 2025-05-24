from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from expenses.models import Expense, DailyAllowance
from accountant.services.approval_flow import process_expense_action
from accountant.views.common import is_accountant
from collections import defaultdict



@login_required
@user_passes_test(is_accountant)
def expense_approval_dashboard(request):
    expenses = Expense.objects.select_related('employee__user', 'project', 'new_expense_type')
    das = DailyAllowance.objects.select_related('employee__user', 'project')

    # Filters
    project_id = request.GET.get('project')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if project_id:
        expenses = expenses.filter(project_id=project_id)
        das = das.filter(project_id=project_id)
    if status:
        expenses = expenses.filter(status=status)
        if status == "Approved":
            das = das.filter(approved=True)
        elif status == "Rejected":
            das = das.none()
        else:
            das = das.filter(approved=False)
    if start_date and end_date:
        expenses = expenses.filter(date__range=[start_date, end_date])
        das = das.filter(date__range=[start_date, end_date])

    # Grouping by (date, employee_id, project_id)
    grouped_data = defaultdict(lambda: {"expenses": [], "da": None})
    for exp in expenses:
        key = (exp.date, exp.employee_id, exp.project_id)
        grouped_data[key]["expenses"].append(exp)

    for da in das:
        key = (da.date, da.employee_id, da.project_id)
        grouped_data[key]["da"] = da

    # Reformat key for template-friendly access
    formatted_grouped = {}
    for key, value in grouped_data.items():
        date_val, employee_id, project_id = key
        ref_obj = value["expenses"][0] if value["expenses"] else value["da"]
        if ref_obj:
            display_key = type("GroupKey", (object,), {
                "date": date_val,
                "employee": ref_obj.employee,
                "project": ref_obj.project
            })()
            formatted_grouped[display_key] = value

    return render(request, 'accountant/expense_approval_dashboard.html', {
        'grouped_data': formatted_grouped,
        'projects': Expense.objects.values('project__id', 'project__name').distinct(),
    })


@require_POST
@login_required
@user_passes_test(is_accountant)
def approve_or_reject_expense(request, expense_id, action):
    expense = get_object_or_404(Expense, id=expense_id)
    remark = request.POST.get("remark", "").strip()

    if not remark:
        messages.error(request, "Remark is required for both approval and rejection.")
        return redirect('accountant:expense-approval')

    if expense.status == 'Pending':
        process_expense_action(expense, action, remark, request)

    return redirect('accountant:expense-approval')




@login_required
@user_passes_test(is_accountant)
def approve_daily_allowance(request, da_id):
    da = get_object_or_404(DailyAllowance, id=da_id)

    if not da.approved:
        da.approved = True
        da.save()
        messages.success(request, f"DA for {da.employee.user.get_full_name()} on {da.date} approved.")
    else:
        messages.info(request, "DA is already approved.")

    return redirect('accountant:expense-approval')
