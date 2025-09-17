# skills/templatetags/skill_extras.py
from django import template

register = template.Library()

@register.filter(is_safe=False)
def split(value, sep=None):
    """
    Split a string by `sep` and return a list. If sep is None or empty,
    split on whitespace (Python's default). If value is not a string,
    return it unchanged.
    Usage in template: {{ some_string|split:"," }}
    """
    if value is None:
        return []
    # protect against non-string input
    try:
        s = str(value)
    except Exception:
        return value
    if sep in (None, ''):
        return s.split()
    return s.split(sep)


@register.filter
def get_item(mapping, key):
    """
    Safe dict/list lookup in template: mapping|get_item:key
    Works for dicts, QueryDict-like objects, lists (index).
    """
    try:
        # if mapping is a dict-like
        if mapping is None:
            return None
        if isinstance(mapping, dict):
            return mapping.get(key)
        # try numeric index if key is numeric string
        try:
            ik = int(key)
        except Exception:
            ik = None
        if ik is not None and hasattr(mapping, '__len__') and not isinstance(mapping, dict):
            try:
                return mapping[ik]
            except Exception:
                pass
        # fallback to attribute access
        return getattr(mapping, key, None)
    except Exception:
        return None


