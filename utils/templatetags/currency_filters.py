from django import template
from utils.currency import format_currency

register = template.Library()

@register.filter
def currency_display(value, currency_code):
    return format_currency(value, currency_code)
