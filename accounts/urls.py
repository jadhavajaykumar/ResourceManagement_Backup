# accounts/urls.py
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from employee.views.profile_views import profile_home
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.custom_login, name='login'),  # <== FIXED HERE
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('profile/', profile_home, name='profile'),
    path('dashboard/', include(('dashboard.urls', 'dashboard'), namespace='dashboard')),
    path('change-user-role/', views.change_user_role, name='change-user-role'),
]