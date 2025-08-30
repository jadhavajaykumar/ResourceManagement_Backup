from django import template
from utils.currency import format_currency as format_currency_util

register = template.Library()

@register.filter(name='format_currency')
def format_currency(amount, currency):
    return format_currency_util(amount, currency)
