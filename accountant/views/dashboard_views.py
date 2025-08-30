from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('expenses.can_settle')
def accountant_dashboard(request):
    return render(request, 'accountant/accountant_dashboard.html')