from .dashboard_views import *
from .approval_views import *
from .export_views import *

from django.urls import reverse
from django.http import HttpResponse


def debug_urls(request):
    urls = [
        reverse('accountant:accountant_approve_advance', args=[1]),
        reverse('accountant:accountant_approve_advances'),
        reverse('accountant:expense-approval-dashboard'),
    ]
    content = "<br>".join(urls)
    return HttpResponse(content)

