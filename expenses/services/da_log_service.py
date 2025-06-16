from expenses.models import DailyAllowanceLog

def log_da_action(da_entry, action, performed_by, remark=''):
    DailyAllowanceLog.objects.create(
        da_entry=da_entry,
        action=action,
        performed_by=performed_by,
        remark=remark
    )
