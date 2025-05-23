from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from accountant.views.common import is_accountant

@login_required
@user_passes_test(is_accountant)
def accountant_dashboard(request):
    return render(request, 'accountant/accountant_dashboard.html')
    
    