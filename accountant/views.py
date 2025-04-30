from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.utils.timezone import localtime
from django.http import HttpResponse
from django.contrib import messages
from expenses.models import Expense
import pandas as pd
from io import BytesIO


def is_accountant(user):
    return user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(is_accountant)
def accountant_dashboard(request):
    return render(request, 'accountant/accountant_dashboard.html')


@login_required
@user_passes_test(is_accountant)
def expense_approval_dashboard(request):
    expenses = Expense.objects.select_related('employee__user', 'project', 'new_expense_type').all()


    # Filters
    project_id = request.GET.get('project')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if project_id:
        expenses = expenses.filter(project_id=project_id)
    if status:
        expenses = expenses.filter(status=status)
    if start_date and end_date:
        expenses = expenses.filter(date__range=[start_date, end_date])

    if 'export' in request.GET:
        return export_expenses_to_excel(expenses)

    return render(request, 'accountant/expense_approval_dashboard.html', {
        'expenses': expenses,
        'projects': Expense.objects.values('project__id', 'project__name').distinct(),
    })


def export_expenses_to_excel(expenses_queryset):
    data = []
    for e in expenses_queryset:
        data.append({
            "Employee": e.employee.user.get_full_name(),
            "Project": e.project.name if e.project else "",
            "Date": localtime(e.date).strftime("%Y-%m-%d"),
            "Expense Type": e.expense_type.name if e.expense_type else "",
            "Kilometers": e.kilometers,
            "Amount (₹)": e.amount,
            "Status": e.status,
            "Receipt": e.receipt.url if e.receipt else "",
            "Comments": e.comments or "",
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Expenses')

    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=expenses_export.xlsx'
    return response


@login_required
@user_passes_test(is_accountant)
def approve_or_reject_expense(request, expense_id, action):
    expense = get_object_or_404(Expense, id=expense_id)
    if expense.status == 'Pending':
        if action == 'approve':
            expense.status = 'Approved'
            messages.success(request, f"Expense #{expense.id} approved.")
        elif action == 'reject':
            expense.status = 'Rejected'
            messages.warning(request, f"Expense #{expense.id} rejected.")
        expense.save()
    else:
        messages.info(request, f"Expense #{expense.id} already {expense.status.lower()}.")
    return redirect('accountant:expense-approval')
