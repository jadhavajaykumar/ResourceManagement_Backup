# expenses/templatetags/unique_id.py
import uuid
from django import template

register = template.Library()

@register.simple_tag
def unique_id(prefix="id"):
    """
    Returns a short, reasonably-unique id string like: prefix_4f3a2b8c
    Use as: {% unique_id "filters" as filter_prefix %}
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"
