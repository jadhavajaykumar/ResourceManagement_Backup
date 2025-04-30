from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Usage: {{ value|replace:"old,new" }}
    Replaces 'old' with 'new' in the string.
    """
    try:
        old, new = arg.split(',')
        return value.replace(old, new)
    except ValueError:
        return value  # Fail silently


