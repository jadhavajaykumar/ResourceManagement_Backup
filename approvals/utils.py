# approvals/utils.py
from typing import Optional
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

User = get_user_model()


def get_instance_for_object(obj):
    """
    Return the active (unfinished) ApprovalInstance for `obj`, or None.
    """
    from .models import ApprovalInstance
    ctype = ContentType.objects.get_for_model(obj.__class__)
    return ApprovalInstance.objects.filter(content_type=ctype, object_id=obj.pk, finished=False).first()


def user_matches_selector(user: User, selector_type: str, selector_value: str, obj: Optional[object] = None) -> bool:
    """
    Return True if the user matches the selector described by (selector_type, selector_value).
    If `obj` is provided and selector_type/selector_value indicate reporting manager,
    enforce that the employee's reporting_manager is this user (exact match) where possible.
    """
    if user is None:
        return False

    st = (selector_type or "").strip().lower()
    sv = (selector_value or "").strip()

    # USER
    if st == "user":
        try:
            uid = int(sv)
            return user.pk == uid
        except Exception:
            # check username or email
            return user.username == sv or user.email.lower() == sv.lower()

    # GROUP
    if st == "group":
        return user.groups.filter(name__iexact=sv).exists()

    # ROLE
    if st == "role":
        role = sv.lower()
        # reporting_manager handling: if obj is provided, try to match exact reporting_manager
        if role in ("reporting_manager", "reporting manager", "manager"):
            if obj is not None:
                try:
                    emp = getattr(obj, "employee", None)
                    if emp is not None:
                        rm = getattr(emp, "reporting_manager", None)
                        if rm is not None:
                            # rm may be a User instance or storing id or email/username string
                            if hasattr(rm, "pk"):
                                return rm.pk == user.pk
                            try:
                                if int(rm) == user.pk:
                                    return True
                            except Exception:
                                pass
                            # try to match by username/email if rm is string
                            try:
                                if isinstance(rm, str):
                                    if user.username == rm or user.email.lower() == rm.lower():
                                        return True
                            except Exception:
                                pass
                except Exception:
                    pass
            # fallback: check user's role or group membership
            try:
                ep = getattr(user, "employeeprofile", None)
                if ep and getattr(ep, "role", None):
                    if ep.role.strip().lower() in ("manager", "reporting manager", "reporting_manager"):
                        return True
            except Exception:
                pass
            return user.groups.filter(name__icontains="manager").exists()

        # accountant mapping
        if role in ("accountant", "accounts"):
            return user.groups.filter(name__icontains="accountant").exists()

        # account manager mapping
        if role in ("account_manager", "account manager"):
            return user.groups.filter(name__icontains="account manager").exists()

    return False

