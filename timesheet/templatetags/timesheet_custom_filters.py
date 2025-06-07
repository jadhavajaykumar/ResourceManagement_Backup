from django import template
from collections import defaultdict
from itertools import groupby
from operator import attrgetter


register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)



@register.filter
def get_range(start, end):
    return range(int(start), int(end) + 1)



@register.filter
def group_by_date(entries):
    grouped = defaultdict(list)
    for entry in entries:
        grouped[entry.date].append(entry)
    return grouped.items()
