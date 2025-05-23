def is_accountant(user):
    return (
        user.is_authenticated and
        hasattr(user, 'employeeprofile') and
        user.employeeprofile.role == 'Accountant'
    )