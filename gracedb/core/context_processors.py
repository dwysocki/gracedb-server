from django.conf import settings


def LigoDebugContext(request):
    if hasattr(settings, 'CONFIG_NAME'):
        return { 'config_name': settings.CONFIG_NAME }
    return {}
