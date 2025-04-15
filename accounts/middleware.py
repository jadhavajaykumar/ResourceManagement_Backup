#accounts\middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.utils.cache import add_never_cache_headers
from django.http import HttpResponseRedirect



class DisableClientSideCachingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not isinstance(response, HttpResponseRedirect):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response