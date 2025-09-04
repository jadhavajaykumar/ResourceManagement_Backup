from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required




@login_required
def raise_advance_request(request):
    return redirect('employee:unified-expense-dashboard')





@login_required
def list_advance_requests(request):
    return redirect('expenses:unified-expense-dashboard')

