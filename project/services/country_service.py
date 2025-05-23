# project/services/country_service.py

from expenses.models import CountryDARate

def get_country_rate_details(country_id):
    try:
        country = CountryDARate.objects.get(id=country_id)
        return {
            'da_rate_per_hour': str(country.da_rate_per_hour),
            'extra_hour_rate': str(country.extra_hour_rate),
            'currency': country.currency,
        }
    except CountryDARate.DoesNotExist:
        return None
