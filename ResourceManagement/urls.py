from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.staticfiles.views import serve
#from . import views


def root_redirect(request):
    return redirect('accounts:login')

urlpatterns = [
    path('', root_redirect, name='root'),  # Redirect root to login
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('employee/', include('employee.urls')),
    path('project/', include('project.urls')),
    path('timesheet/', include('timesheet.urls')),
    path('expenses/', include('expenses.urls')),
    path('manager/', include('manager.urls')),
    path('docgen/', include('docgen.urls')),
    path('accountant/', include('accountant.urls')),
    


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)









