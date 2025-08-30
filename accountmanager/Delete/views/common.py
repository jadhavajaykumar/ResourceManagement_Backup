from employee.models import EmployeeProfile

def is_accountmanager(user):
    return hasattr(user, 'employeeprofile') and user.employeeprofile.role == 'Account Manager'
