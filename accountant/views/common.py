def is_accountant(user):
    return user.is_authenticated and user.has_perm('expenses.can_settle')