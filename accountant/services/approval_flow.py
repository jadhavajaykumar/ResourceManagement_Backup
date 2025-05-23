from django.contrib import messages

def process_expense_action(expense, action, remark, request):
    expense.accountant_remark = remark
    if action == 'approve':
        expense.status = 'Forwarded to Manager'
        messages.success(request, f"Expense #{expense.id} forwarded to Manager.")
    elif action == 'reject':
        expense.status = 'Rejected'
        messages.warning(request, f"Expense #{expense.id} rejected.")
    expense.save()