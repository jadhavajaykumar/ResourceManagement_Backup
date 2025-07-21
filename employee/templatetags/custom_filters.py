# employee/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtract arg from value"""
    return value - arg