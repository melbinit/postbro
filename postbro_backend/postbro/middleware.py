"""
Custom middleware for development - allows ngrok domains
"""
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import Http404


class AllowNgrokHostsMiddleware:
    """
    Middleware to allow ngrok domains in DEBUG mode
    Must be placed BEFORE SecurityMiddleware to override host validation
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            host = request.get_host().split(':')[0]  # Remove port if present
            # Allow ngrok domains by adding to ALLOWED_HOSTS before SecurityMiddleware checks
            ngrok_domains = ['.ngrok-free.app', '.ngrok.io', '.loca.lt', '.ngrok.app']
            if any(host.endswith(domain) for domain in ngrok_domains):
                if host not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(host)
        
        response = self.get_response(request)
        return response

