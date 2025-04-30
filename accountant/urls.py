from django.urls import path
from . import views

app_name = 'accountant'

urlpatterns = [
    path('expenses/', views.expense_approval_dashboard, name='expense-approval'),
    path('expenses/<int:expense_id>/<str:action>/', views.approve_or_reject_expense, name='expense-action'),
    path('dashboard/', views.accountant_dashboard, name='dashboard')

]
