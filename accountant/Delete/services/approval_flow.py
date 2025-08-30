# accountant/services/approval_flow.py

from django.contrib import messages
from django.db import transaction
from expenses.models import AdvanceRequest

def process_expense_action(expense, action, remark, request):
    from django.db import transaction
    from expenses.models import AdvanceRequest

    expense.accountant_remark = remark

    if action == 'approve':
        with transaction.atomic():
            # Find the most recent settled advance for the same project
            advance = AdvanceRequest.objects.filter(
                employee=expense.employee,
                project=expense.project,
                approved_by_accountant=True,
                settled_by_account_manager=True
            ).order_by('-date_requested').first()

            if advance:
                # Link expense to advance
                expense.advance_used = advance
                
                # DEBUG: Print advance details
                print(f"Linking expense {expense.id} to advance {advance.id}")
                print(f"Advance amount: {advance.amount}, Current balance: {advance.current_balance()}")
                
                # Save expense first to ensure link is established
                expense.status = 'Approved'
                expense.final_status = 'Approved'
                expense.save()
                
                # Recalculate advance balance
                new_balance = advance.current_balance()
                print(f"New advance balance after deduction: {new_balance}")
                
                messages.success(request, f"₹{expense.amount} deducted from Advance ID #{advance.id}. New balance: ₹{new_balance}")
            else:
                expense.status = 'Approved'
                expense.final_status = 'Approved'
                expense.save()
                messages.info(request, "Expense approved but not linked to any advance.")

    elif action == 'reject':
        expense.status = 'Rejected'
        expense.final_status = 'Rejected'
        expense.save()
        messages.warning(request, f"Expense #{expense.id} rejected.")

