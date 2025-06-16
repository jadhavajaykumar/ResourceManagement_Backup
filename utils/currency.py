def get_currency_symbol(currency):
    symbols = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'Dollar': '$',
        'Rupee': '₹',
        '₹': '₹',
        '$': '$',
    }
    return symbols.get(currency, f'{currency} ')

def format_currency(amount, currency):
    try:
        from decimal import Decimal, InvalidOperation
        if isinstance(amount, str):
            amount = amount.strip().split()[-1]  # keep just the numeric part
        amount = Decimal(amount)
        symbol = get_currency_symbol(currency)
        return f"{symbol}{amount.quantize(Decimal('1.00'))}"
    except (ValueError, InvalidOperation, TypeError):
        return f"{amount} {currency}"  # fallback
