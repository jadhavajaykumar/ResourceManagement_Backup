from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from expenses.models import Expense, DailyAllowance
from accountant.services.approval_flow import process_expense_action
from accountant.views.common import is_accountant


from django.db.models import Q

# accountant/views/expense_approval_dashboard.py



from accountant.views.common import is_accountant
from collections import defaultdict
from datetime import datetime


@login_required
@user_passes_test(is_accountant)
def expense_approval_dashboard(request):
    expenses = Expense.objects.select_related('employee__user', 'project', 'new_expense_type').all()
    das = DailyAllowance.objects.select_related('employee__user', 'project').all()

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
            das = das.none()  # No rejected field; adjust if needed
        else:
            das = das.filter(approved=False)
    if start_date and end_date:
        expenses = expenses.filter(date__range=[start_date, end_date])
        das = das.filter(date__range=[start_date, end_date])

    # Group both expenses and DAs under a common key: (date, employee_id, project_id)
    grouped_data = defaultdict(lambda: {"expenses": [], "da": None})
    for exp in expenses:
        key = (exp.date, exp.employee.id, exp.project.id)
        grouped_data[key]["expenses"].append(exp)

    for da in das:
        key = (da.date, da.employee.id, da.project.id)
        grouped_data[key]["da"] = da

    # Reformat keys for display in template: replace tuple with an object for cleaner access
    formatted_grouped = {}
    for key, val in grouped_data.items():
        date_val, employee_id, project_id = key
        if val["expenses"]:
            sample = val["expenses"][0]
        elif val["da"]:
            sample = val["da"]
        else:
            continue  # skip if no data at all (shouldn't happen)
        display_key = type("GroupKey", (object,), {
            "date": date_val,
            "employee": sample.employee,
            "project": sample.project
        })()
        formatted_grouped[display_key] = val

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