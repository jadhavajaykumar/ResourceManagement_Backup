# expenses/templatetags/custom_filters.py
from django import template
register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    try:
        return dictionary.get(key, {})
    except Exception as e:
        return {}


@register.filter
def sum_length(value, field):
    """Improved sum_length filter that handles both dict and list structures"""
    total = 0
    if isinstance(value, dict):
        for employee, entries in value.items():
            for entry in entries:
                if field == 'expenses':
                    total += len(entry.get('expenses', []))
                elif field == 'da' and entry.get('da'):
                    total += 1
    return total


@register.filter
def sum_expenses_and_da(records):
    """Count expenses and DA in a record list"""
    counts = {
        'expenses': 0,
        'da': 0
    }
    for entry in records:
        counts['expenses'] += len(entry.get('expenses', []))
        if entry.get('da'):
            counts['da'] += 1
    return counts    
    


@register.filter
def dict_get(d, key):
    return d.get(key, [])
    