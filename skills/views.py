from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
# or: from django.shortcuts import render

@login_required
def home(request):
    return HttpResponse("Skills module is alive.")
    # or: return render(request, "skills/home.html")
