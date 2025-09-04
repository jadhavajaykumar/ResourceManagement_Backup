from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from expenses.models import AdvanceRequest




@login_required
def raise_advance_request(request):
    return redirect('employee:unified-expense-dashboard')





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

