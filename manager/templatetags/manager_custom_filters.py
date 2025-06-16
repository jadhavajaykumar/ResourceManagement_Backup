# manager/templatetags/manager_custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary and key in dictionary:
        return dictionary[key]
    return None


@register.filter
def dictkey(d, key):
    return d.get(key)
