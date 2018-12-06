from django.conf import settings

def LigoDebugContext(request):
    if settings.DEBUG and hasattr(settings, 'CONFIG_NAME'):
        return { 'config_name': settings.CONFIG_NAME }
    return {}
