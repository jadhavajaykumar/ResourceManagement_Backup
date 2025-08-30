from django.urls import path
from .views import home   # <-- import the function from views.py

app_name = "skills"

urlpatterns = [
    path("", home, name="skills-home"),
]
