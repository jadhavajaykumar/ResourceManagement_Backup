from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.staticfiles.views import serve
from expenses.views.unified_expense_dashboard import unified_expense_dashboard
#from . import views


def root_redirect(request):
    return redirect('accounts:login')

urlpatterns = [
    path('', root_redirect, name='root'),  # Redirect root to login
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('employee/', include('employee.urls')),
    path('project/', include('project.urls')),
    # main urls.py
    path("timesheet/", include(("timesheet.urls", "timesheet"), namespace="timesheet")),
    #path("accountmanager/", include("accountmanager.urls")),
    path('expenses/', include(('expenses.urls', 'expenses'), namespace='expenses')),
    #path('manager/', include('manager.urls')),
    #path('manager/', include(('manager.urls', 'manager'), namespace='manager')),
    #path('docgen/', include('docgen.urls')),
    path('docgen/', include(('docgen.urls', 'docgen'), namespace='docgen')),
    #path('accountant/', include('accountant.urls')),
    path('unified-expenses/', unified_expense_dashboard, name='unified-expense-dashboard'),
    path('dashboard/', include(('dashboard.urls', 'dashboard'), namespace='dashboard')),
    path('skills/', include(('skills.urls', 'skills'), namespace='skills')),
    
    


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)









