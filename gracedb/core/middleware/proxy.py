from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.http import HttpResponse

class XForwardedForMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if ('HTTP_X_FORWARDED_FOR' in request.META and settings.DEBUG and
            'debug_toolbar' in settings.INSTALLED_APPS):

            # If we're in debugging mode and the debug toolbar is on AND there
            # is a forwarded IP address, then set REMOTE_ADDR to be the value
            # of the HTTP_X_FORWARDED_FOR header. This allows the debug toolbar
            # to work as expected. As of now, there is only one other place in
            # the server code where REMOTE_ADDR is used, and it's handled
            # properly, so this won't affect it.
            request.META['REMOTE_ADDR'] = \
                request.META['HTTP_X_FORWARDED_FOR'].split(",")[0].strip()
