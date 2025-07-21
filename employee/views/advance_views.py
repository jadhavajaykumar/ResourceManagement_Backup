from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from expenses.forms import AdvanceRequestForm
from expenses.models import AdvanceRequest
import logging
logger = logging.getLogger(__name__)



@login_required
def raise_advance_request(request):
    employee = request.user.employeeprofile
    last_advance = AdvanceRequest.objects.filter(
        employee=employee,
        approved_by_accountant=True
    ).order_by('-date_requested').first()
    
    if last_advance:
        logger.info(f"Advance ID: {last_advance.id}, Balance: {last_advance.current_balance()}")

    # ❌ Block only if balance is positive
    if last_advance and last_advance.current_balance() > 0:
        balance = last_advance.current_balance()
        return render(request, 'employee/advance_blocked.html', {
            'advance': last_advance,
            'balance': balance,
        })
    
    form = AdvanceRequestForm(request.POST or None, employee=employee)
    if form.is_valid():
        advance = form.save(commit=False)
        advance.employee = employee
        advance.save()
        return redirect('employee:advance-requests')

    return render(request, 'employee/raise_advance.html', {'form': form})





@login_required
def list_advance_requests(request):
    employee = request.user.employeeprofile
    advances = AdvanceRequest.objects.filter(employee=employee).order_by('-date_requested')

    latest_advance = advances.first()
    current_balance = latest_advance.current_balance() if latest_advance else None
    
    

    return render(request, 'employee/my_advance_requests.html', {
        'advances': advances,
        'latest_advance': latest_advance,
        'current_balance': current_balance,
        #'allow_new_advance': allow_new_advance,  # ✅ Fix applied
    })

