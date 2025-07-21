from django.core.management.base import BaseCommand
from expenses.models import AdvanceRequest
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Sync AdvanceRequest.balance field with current_balance() method'

    def handle(self, *args, **options):
        mismatches = []

        for adv in AdvanceRequest.objects.select_related('employee__user', 'project'):
            correct_balance = adv.current_balance()
            if float(adv.balance) != float(correct_balance):
                mismatches.append({
                    'id': adv.id,
                    'employee_name': adv.employee.user.get_full_name(),
                    'employee_email': adv.employee.user.email,
                    'project_name': adv.project.name,
                    'old_balance': float(adv.balance),
                    'new_balance': float(correct_balance),
                })
                adv.balance = correct_balance
                adv.save()

        if mismatches:
            self.stdout.write(self.style.SUCCESS("✅ Fixed AdvanceRequest Balances:\n"))
            for item in mismatches:
                self.stdout.write(
                    f"Advance ID: {item['id']} | "
                    f"Employee: {item['employee_name']} <{item['employee_email']}> | "
                    f"Project: {item['project_name']} | "
                    f"Old Balance: {item['old_balance']} → New Balance: {item['new_balance']}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("✅ All AdvanceRequest balances are already correct."))
