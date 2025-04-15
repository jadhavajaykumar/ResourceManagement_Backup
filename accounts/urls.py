# accounts/urls.py
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(
        template_name='accounts/login.html',
        redirect_authenticated_user=True,
        redirect_field_name='next'
    ), name='login'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('profile/', views.redirect_to_dashboard, name='profile'),
    path('change-user-role/', views.change_user_role, name='change-user-role'),
]