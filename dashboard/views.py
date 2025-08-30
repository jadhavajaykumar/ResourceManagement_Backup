from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from accounts.utils import get_effective_role


@login_required
def home(request):
    """Render a menu based on the user's role."""
    role = get_effective_role(request.user)
    menu_items = []

    # All users can access their employee dashboard
    menu_items.append({
        "label": "Employee Dashboard",
        "url": reverse("employee:employee-dashboard"),
    })

    if role in ["Manager", "Director"]:
        menu_items.append({
            "label": "Manager Dashboard",
            "url": reverse("manager:manager-dashboard"),
        })

    if role in ["AccountManager", "Director"]:
        menu_items.append({
            "label": "Account Manager Dashboard",
            "url": reverse("accountmanager:dashboard"),
        })

    if role in ["Accountant", "Director"]:
        menu_items.append({
            "label": "Accountant Dashboard",
            "url": reverse("accountant:dashboard"),
        })

    if request.user.is_superuser:
        menu_items.append({
            "label": "Admin", 
            "url": reverse("admin:index"),
        })

    context = {"menu_items": menu_items}
    return render(request, "dashboard/home.html", context)