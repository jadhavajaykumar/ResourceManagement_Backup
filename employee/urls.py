from django.urls import path
from . import views

app_name = 'employee'

urlpatterns = [
    path('profile/', views.profile_home, name='employee-profile-home'),
    path('edit-profile/', views.edit_profile, name='edit-profile'),
    path('dashboard/', views.employee_dashboard, name='employee-dashboard'),
    path('my-projects/', views.my_projects, name='my-projects'),
]