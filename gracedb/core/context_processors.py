
from django.conf import settings

def LigoDebugContext(request):
    if settings.DEBUG and settings.DEBUG != "PRODUCTION":
        return { 'config_name' : settings.CONFIG_NAME }
    return {}
