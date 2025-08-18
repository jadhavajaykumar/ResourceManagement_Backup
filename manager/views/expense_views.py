from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from expenses.models import Expense
from accounts.access_control import is_manager
from employee.models import EmployeeProfile
from expenses.models import AdvanceRequest



def get_reportees(user):
    return EmployeeProfile.objects.filter(reporting_manager=user)

@user_passes_test(is_manager)
@login_required
def expense_approval_dashboard(request):
    reportees = get_reportees(request.user)

    # Tab 1: Accountant Approved (Manager can approve/reject)
    accountant_approved = Expense.objects.filter(
        employee__in=reportees,
        status='Forwarded to Manager',
        forwarded_to_manager=True
    ).select_related('employee__user', 'project', 'new_expense_type')

    # Tab 2: Forwarded to Account Manager
    forwarded_expenses = Expense.objects.filter(
        employee__in=reportees,
        status='Forwarded to Account Manager',
        forwarded_to_accountmanager=True
    ).select_related('employee__user', 'project', 'new_expense_type')

    # Tab 3: Rejected
    rejected_expenses = Expense.objects.filter(
        employee__in=reportees,
        status='Rejected'
    ).select_related('employee__user', 'project', 'new_expense_type')

    # Tab 4: Advance Requests
    advance_requests = AdvanceRequest.objects.filter(
        approved_by_manager=False,
        employee__in=reportees
    )

    context = {
        'accountant_approved': accountant_approved,   # renamed tab 1
        'forwarded_expenses': forwarded_expenses,     # renamed tab 2
        'rejected_expenses': rejected_expenses,
        'advance_requests': advance_requests,
    }
    return render(request, 'manager/expense_approval_dashboard.html', context)



@user_passes_test(is_manager)
@login_required
def expense_approvals(request):
    reportees = get_reportees(request.user)
    pending_exp = Expense.objects.filter(status='SUBMITTED', employee__in=reportees)
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html_snippet = render_to_string('manager/partials/expense_table_rows.html', {'expenses': pending_exp})
        return HttpResponse(html_snippet)
    context = {'expenses': pending_exp, 'current_page': 'expenses'}
    return render(request, 'manager/expense_approvals.html', context)

@user_passes_test(is_manager)
@login_required
def handle_expense_action(request, expense_id, action):
    expense = get_object_or_404(Expense, id=expense_id)

    if expense.employee.reporting_manager != request.user:
        messages.error(request, "You can only process expenses from your direct reportees.")
        return redirect('manager:expense-approval')

    if request.method == 'POST':
        remark = request.POST.get('manager_remark', '').strip()

        if not remark:
            messages.error(request, "Remark is required.")
            return redirect('manager:expense-approval')

        if action == 'approve':
            expense.status = 'Forwarded to Account Manager'
            expense.forwarded_to_accountmanager = True
            expense.manager_remark = remark
            messages.success(request, "Expense approved.")
            notify_employee(expense, 'Approved', remark)

        elif action == 'reject':
            expense.status = 'Rejected'
            expense.manager_remark = remark
            messages.success(request, "Expense rejected.")
            notify_employee(expense, 'Rejected', remark)

        else:
            messages.error(request, "Invalid action.")
            return redirect('manager:expense-approval')

        expense.save()
        return redirect('manager:expense-approval')

    return redirect('manager:expense-approval')


def notify_employee(expense, action, remark):
    subject = f"Your expense has been {action}"
    message = f"""
Dear {expense.employee.user.get_full_name()},

Your expense submitted on {expense.date} for project '{expense.project.name}' has been {action.lower()} by your manager.

Manager Remark:
{remark or 'No remarks provided.'}

Regards,
Accounts Team
"""
    send_mail(
        subject,
        message,
        'noreply@yourcompany.com',
        [expense.employee.user.email],
        fail_silently=True,
    )
