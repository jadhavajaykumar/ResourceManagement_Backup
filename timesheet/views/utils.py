# approvals/utils.py
from django.contrib.contenttypes.models import ContentType
from .models import ApprovalInstance

def user_matches_selector(user, selector_type, selector_value):
    # selector_type: "role", "group", "user"
    if selector_type == "role":
        ep = getattr(user, "employeeprofile", None)
        return bool(ep and getattr(ep, "role", "").strip().lower() == str(selector_value).strip().lower())
    if selector_type == "group":
        return user.groups.filter(name=selector_value).exists()
    if selector_type == "user":
        try:
            return int(selector_value) == int(user.id)
        except Exception:
            return False
    return False

def get_instance_for_object(obj):
    ct = ContentType.objects.get_for_model(obj)
    return ApprovalInstance.objects.filter(content_type=ct, object_id=obj.id).first()
