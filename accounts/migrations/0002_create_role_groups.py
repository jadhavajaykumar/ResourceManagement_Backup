from django.db import migrations

def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    manager_group, _ = Group.objects.get_or_create(name='Manager')
    accountant_group, _ = Group.objects.get_or_create(name='Accountant')
    account_manager_group, _ = Group.objects.get_or_create(name='Account Manager')

    try:
        approve_perm = Permission.objects.get(codename='can_approve', content_type__app_label='timesheet')
        settle_perm = Permission.objects.get(codename='can_settle', content_type__app_label='expenses')
    except Permission.DoesNotExist:
        return

    manager_group.permissions.add(approve_perm)
    accountant_group.permissions.add(settle_perm)
    account_manager_group.permissions.add(settle_perm)


def remove_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['Manager', 'Accountant', 'Account Manager']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('timesheet', '0002_timesheet_permissions'),
        ('expenses', '0011_expense_permissions'),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]