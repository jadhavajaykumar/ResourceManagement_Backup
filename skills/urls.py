from django.urls import path
from .views import home   # <-- import the function from views.py

urlpatterns = [
    path("", home, name="skills-home"),
]
